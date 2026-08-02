from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db.session import engine
from backend.app.models.base import Base
from backend.app.routers import auth, chat, trips

# 必须在 create_all 之前导入所有 model，否则它们不会注册到 Base.metadata
import backend.app.models.user  # noqa: F401
import backend.app.models.trip  # noqa: F401
import backend.app.models.message  # noqa: F401
from backend.app.db.redis import init_redis, close_redis


from backend.app.middleware.auth_middleware import jwt_middleware




@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时根据 ORM 定义自动建表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()

app = FastAPI(title="旅游助手 Agent API", version="0.5.0", lifespan=lifespan)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # 不设 allow_credentials，因为用 Authorization header 传 token，不需要 cookie
)

# JWT 鉴权中间件 — 对所有非公开路径校验 token
app.middleware("http")(jwt_middleware)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(trips.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
