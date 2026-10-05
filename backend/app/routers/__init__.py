"""routers 注册中心 — 统一导出各路由模块与公共依赖"""

from fastapi import FastAPI

from backend.app.routers import auth, chat, trips
from backend.app.routers.dependencies import get_current_user, ip_ratelimit


def register_routers(app: FastAPI) -> None:
    """统一挂载所有路由"""
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(trips.router)


__all__ = ["auth", "chat", "trips", "get_current_user", "ip_ratelimit", "register_routers"]
