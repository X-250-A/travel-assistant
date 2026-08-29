"""models 注册中心 — 统一导出所有 ORM 模型"""
from backend.app.models.base import Base
from backend.app.models.message import Message
from backend.app.models.trip import Trip
from backend.app.models.user import User

__all__ = ["Base", "User", "Message", "Trip"]
