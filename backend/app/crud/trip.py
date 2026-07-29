"""
Trip CRUD 操作
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.trip import Trip
from backend.app.models.message import Message
from sqlalchemy import delete as sa_delete

# 创建行程
async def create_trip(db: AsyncSession, user_id: int, title: str = "", status: str = "draft"):
    trip = Trip(
        user_id = user_id,
        title = title,
        status = status,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


# 通过id查询指定行程
async def find_trip_by_id(db: AsyncSession, trip_id: int):
    query = select(Trip).where(Trip.id == trip_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# 查询用户行程列表
async def list_user_trips(db: AsyncSession, user_id: int, page: int, page_size: int):
    query = (select(Trip)
        .where(Trip.user_id == user_id)
        .order_by(Trip.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all()

# 更新行程
async def update_trip(
    db: AsyncSession,
    trip_id: int,
    *,
    title: str | None = None,
    status: str | None = None,
    plan_data: dict | None = None,
):
    """更新行程字段，只更新传入的非 None 字段"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        return None
    if title is not None:
        trip.title = title
    if status is not None:
        trip.status = status
    if plan_data is not None:
        trip.plan_data = plan_data

    await db.commit()
    await db.refresh(trip)
    return trip



async def delete_trip(db: AsyncSession, trip_id: int):
    """删除行程及其关联消息（先删子表记录，避免外键约束冲突）"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        return None
    await db.execute(sa_delete(Message).where(Message.trip_id == trip_id))
    await db.delete(trip)
    await db.commit()
    return trip





