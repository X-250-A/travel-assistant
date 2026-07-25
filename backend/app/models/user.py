"""
User 实体
"""
from backend.app.models.base import Base
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, comment="用户id")
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
