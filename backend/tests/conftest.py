"""测试基础设施 — fixtures 集中定义

所有测试文件通过 fixtures 获得：
- 隔离的异步数据库 session（每测事务回滚）
- httpx AsyncClient（FastAPI TestClient）
- 已认证的 Authorization header
"""

import os
import sys
import tempfile
from unittest.mock import AsyncMock, patch

# bcrypt 5.0 与 passlib 不兼容：
#   1) bcrypt 5.0 移除了 __about__，passlib 靠它检测版本
#   2) bcrypt 5.0 拒绝 >72 字节的密码，但 passlib 内部 detect_wrap_bug()
#      传入了 256 字节的测试秘密，导致 import 时崩溃
# 这里在 passlib 加载前做兼容处理。
import bcrypt as _bcrypt  # noqa: E402
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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

# 测试数据库放在系统临时目录、每次会话新建：行为与项目内文件库一致（双引擎共享同一文件），
# 但每次运行都是全新空库，且不需要删除文件——沙箱/CI 下文件删除可能被拦截，
# 项目目录内残留库跨会话复用时数据不干净，会引发偶发失败（如 register 撞"用户名已存在"）
_TEST_DB_DIR = tempfile.mkdtemp(prefix="trip_agent_test_")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_DIR}/test.db"
os.environ["DEEPSEEK_API_KEY"] = "sk-test-dummy-key"
os.environ["DEEPSEEK_BASE_URL"] = "https://test-deepseek.example.com/v1"
os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-flash"
# Critic 审查走真实 LLM 调用，测试环境必须关闭，避免现有测试真打 DeepSeek API
os.environ.setdefault("CRITIC_ENABLED", "false")
# 向量记忆 embedding 走真实 SiliconFlow API；测试环境必须用假 key（含 change-me），
# 让 EmbeddingClient.available() 返回 False，整条链路静默跳过，避免真打 SiliconFlow
os.environ["SILICONFLOW_API_KEY"] = "sk-test-dummy-key-change-me"
os.environ["AMAP_API_KEY"] = "test-amap-key-for-tests"

# ── 现在可安全导入项目模块 ──
import backend.app.models.message  # noqa: E402, F401
import backend.app.models.trip  # noqa: E402, F401

# 显式导入所有模型，确保 Base.metadata 注册完整
import backend.app.models.user  # noqa: E402, F401
from backend.app.config import settings  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402
from backend.app.main import app as fastapi_app  # noqa: E402
from backend.app.models.base import Base  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# 数据库 fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """会话级：创建测试数据库引擎 + 建表（每次会话全新临时库，无需清理）"""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


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


@pytest_asyncio.fixture(autouse=True)
async def mock_redis():
    """全局 mock Redis：中间件 / logout 依赖 get_redis，但测试环境不启动 Redis。

    ASGITransport 不触发 lifespan，init_redis() 从未执行；若中间件真的
    调用 get_redis() 会抛 RuntimeError。这里用 AsyncMock 替换 get_redis，
    让 JWT 黑名单检查在测试中走通（默认 token 不在黑名单）。
    """
    mock_r = AsyncMock()
    mock_r.sismember = AsyncMock(return_value=0)  # 不在黑名单
    mock_r.sadd = AsyncMock(return_value=1)
    mock_r.expire = AsyncMock(return_value=True)
    # 用户偏好记忆（memory/preferences.py）：hgetall 返回空 dict = 无历史偏好
    mock_r.hgetall = AsyncMock(return_value={})
    mock_r.hmset = AsyncMock(return_value=True)
    # 限流（ratelimit/core.py）：zremrangebyscore/zadd/zcard 的返回值不被业务使用，
    # 但 zcard 会被拿去和 limit 比较，必须返回 int（1 = 窗口内 1 个请求，≤ limit 放行）
    mock_r.zremrangebyscore = AsyncMock(return_value=1)
    mock_r.zadd = AsyncMock(return_value=1)
    mock_r.zcard = AsyncMock(return_value=1)
    # 天气缓存（tools/weather.py）：get 返回 None = 缓存未命中，走真实 API 分支
    mock_r.get = AsyncMock(return_value=None)
    mock_r.setex = AsyncMock(return_value=True)
    # 各使用点都是 `from ... import get_redis` 的模块级绑定，必须 patch 使用处
    # （注意：dependencies.py 的 ip_ratelimit 挂在 register/login 上，不 patch 会撞真实 Redis）
    patch_targets = [
        "backend.app.middleware.auth_middleware.get_redis",
        "backend.app.routers.auth.get_redis",
        "backend.app.routers.dependencies.get_redis",
        "backend.app.routers.chat.get_redis",
        "backend.app.tools.weather.get_redis",
        "backend.app.tools.poi.get_redis",
    ]
    with (
        patch(patch_targets[0], return_value=mock_r),
        patch(patch_targets[1], return_value=mock_r),
        patch(patch_targets[2], return_value=mock_r),
        patch(patch_targets[3], return_value=mock_r),
        patch(patch_targets[4], return_value=mock_r),
        patch(patch_targets[5], return_value=mock_r),
    ):
        yield mock_r


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
