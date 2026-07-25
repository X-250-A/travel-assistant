"""测试基础设施 — fixtures 集中定义

所有测试文件通过 fixtures 获得：
- 隔离的异步数据库 session（每测事务回滚）
- httpx AsyncClient（FastAPI TestClient）
- 已认证的 Authorization header
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# bcrypt 5.0 与 passlib 不兼容：
#   1) bcrypt 5.0 移除了 __about__，passlib 靠它检测版本
#   2) bcrypt 5.0 拒绝 >72 字节的密码，但 passlib 内部 detect_wrap_bug()
#      传入了 256 字节的测试秘密，导致 import 时崩溃
# 这里在 passlib 加载前做兼容处理。
import bcrypt as _bcrypt  # noqa: E402
if not hasattr(_bcrypt, "__about__"):
    sys.modules["bcrypt"].__about__ = type(sys)("__about__")
    sys.modules["bcrypt"].__about__.__version__ = "5.0.0"
_original_hashpw = _bcrypt.hashpw
def _patched_hashpw(password: bytes, salt: bytes) -> bytes:
    """bcrypt 5.0 严格限制 72 字节，过长时自动截断（仅影响 passlib 内部自测）"""
    if len(password) > 72:
        password = password[:72]
    return _original_hashpw(password, salt)
_bcrypt.hashpw = _patched_hashpw

# ═══════════════════════════════════════════════════════════════════════════
# 环境变量 — 必须在导入任何项目模块之前设置
# pydantic-settings 优先读取 os.environ，覆盖 .env 中的值
# ═══════════════════════════════════════════════════════════════════════════

TEST_DB_PATH = Path(__file__).parent / ".test.db"

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["DEEPSEEK_API_KEY"] = "sk-test-dummy-key"
os.environ["DEEPSEEK_BASE_URL"] = "https://test-deepseek.example.com/v1"
os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-flash"

# ── 现在可安全导入项目模块 ──
from backend.app.config import settings  # noqa: E402
from backend.app.main import app as fastapi_app  # noqa: E402
from backend.app.models.base import Base  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402

# 显式导入所有模型，确保 Base.metadata 注册完整
import backend.app.models.user  # noqa: E402, F401
import backend.app.models.trip  # noqa: E402, F401
import backend.app.models.message  # noqa: E402, F401


# ═══════════════════════════════════════════════════════════════════════════
# 数据库 fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """会话级：创建测试数据库引擎 + 建表 + 结束时清理文件"""
    TEST_DB_PATH.unlink(missing_ok=True)

    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db_session(test_engine):
    """
    函数级：独立事务 session。
    外层 begin() 启动事务 → CRUD 内 commit() 转成 savepoint → 测试结束统一 rollback。
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


# ═══════════════════════════════════════════════════════════════════════════
# FastAPI 测试客户端 fixture
# ═══════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def async_client(db_session):
    """httpx AsyncClient，依赖注入替换为测试 session"""
    async def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# 认证辅助
# ═══════════════════════════════════════════════════════════════════════════

async def _register_and_login(client: AsyncClient, username: str, password: str) -> str:
    """注册用户并登录，返回 'Bearer <token>' 字符串"""
    await client.post("/api/auth/register", json={"username": username, "password": password})
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return f"Bearer {data['access_token']}"


@pytest_asyncio.fixture
async def auth_headers(async_client):
    """默认测试用户的认证 header"""
    return await _register_and_login(async_client, "testuser", "testpass123")


@pytest_asyncio.fixture
async def auth_headers_alt(async_client):
    """第二个测试用户的认证 header（用于权限隔离测试）"""
    return await _register_and_login(async_client, "otheruser", "otherpass456")
