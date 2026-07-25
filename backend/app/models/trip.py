"""
Trip 实体（关联 User）
"""
from backend.app.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, JSON
from typing import Optional

class Trip(Base):
    __tablename__ = 'trip'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="行程ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), comment="用户id")
    title: Mapped[str] = mapped_column(String(200), comment="标题")
    plan_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True,comment="LLM生成的完整行程json")
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="行程状态")


