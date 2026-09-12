"""
Message CRUD 操作
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Message
from backend.app.utils.loggings import crud_logger


# 保存消息
@crud_logger(action="save_message")
async def save_message(db: AsyncSession, trip_id: int, role: str, content: str):
    message = Message(trip_id=trip_id, role=role, content=content)
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


# 查询某个行程的N条消息
async def get_trip_messages(db: AsyncSession, trip_id: int, page: int, page_size: int):
    query = (
        select(Message)
        .where(Message.trip_id == trip_id)
        .order_by(Message.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all()


# 查询某个行程的所有消息
async def get_all_trip_messages(db: AsyncSession, trip_id: int):
    query = select(Message).where(Message.trip_id == trip_id).order_by(Message.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()
