from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db import close_redis, engine, init_redis
from backend.app.logging_config import setup_logging
from backend.app.middleware import jwt_middleware

# 必须在 create_all 之前导入所有 model，否则它们不会注册到 Base.metadata
from backend.app.models import Base, Message, Trip, User  # noqa: F401
from backend.app.routers import auth, chat, trips
from backend.app.exceptions import register_error_handlers

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时根据 ORM 定义自动建表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()

app = FastAPI(title="旅游助手 Agent API", version="0.8.0", lifespan=lifespan)
register_error_handlers(app)



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
