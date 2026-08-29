"""app 顶层注册中心 — 统一导出配置与全部子包"""
from backend.app.config import settings

# 注册全部子包
from backend.app import (
    agent, crud, db, memory, middleware, models,
    ratelimit, routers, schemas, services, tools, utils,
)
from backend.app.main import app

__all__ = [
    "settings",
    "models",
    "schemas",
    "utils",
    "db",
    "crud",
    "memory",
    "services",
    "tools",
    "agent",
    "middleware",
    "ratelimit",
    "routers",
    "app",
]
