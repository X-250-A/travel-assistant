"""app 顶层注册中心 — 统一导出配置与全部子包"""

# 配置必须先于子包导入：crud/utils/services/tools 等大量子模块会在 import 期
# 执行 `from backend.app import settings`。若 settings 后置，包初始化到这里时会
# 因 settings 尚未就位而触发循环导入（ImportError: cannot import name 'settings'）。
# config.py 不依赖 backend.app，可安全提前加载。
from backend.app.config import settings

# 注册全部子包
from backend.app import (
    agent,
    crud,
    db,
    memory,
    middleware,
    models,
    ratelimit,
    routers,
    schemas,
    services,
    tools,
    utils,
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
