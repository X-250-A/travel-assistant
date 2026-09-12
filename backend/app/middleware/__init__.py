"""middleware 注册中心 — 统一导出中间件"""

from backend.app.middleware.auth_middleware import PUBLIC_PATHS, jwt_middleware

__all__ = ["jwt_middleware", "PUBLIC_PATHS"]
