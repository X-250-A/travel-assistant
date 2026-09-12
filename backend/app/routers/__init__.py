"""routers 注册中心 — 统一导出各路由模块与公共依赖"""

from backend.app.routers import auth, chat, trips
from backend.app.routers.dependencies import get_current_user, ip_ratelimit

__all__ = ["auth", "chat", "trips", "get_current_user", "ip_ratelimit"]
