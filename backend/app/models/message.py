"""
Message 实体（关联 Trip，存放对话历史）
"""

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.models.base import Base

class Message(Base):
    __tablename__ = 'message'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="信息ID")
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trip.id"), comment="行程ID")
    role: Mapped[str] = mapped_column(String(20), comment="消息角色：user/assistant/system")
    content: Mapped[str] = mapped_column(Text, comment="消息文本内容")
