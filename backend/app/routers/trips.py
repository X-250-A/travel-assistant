from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.crud import (
    delete_trip,
    find_trip_by_id,
    get_all_trip_messages,
    list_user_trips,
    update_trip,
)
from backend.app.db import get_db
from backend.app.exceptions import ForbiddenError, NotFoundError
from backend.app.models import User
from backend.app.routers.dependencies import get_current_user
from backend.app.schemas import MessageItem, TripListResponse, TripResponse, TripUpdateRequest

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("", response_model=TripListResponse)
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    page_size: int = 100,
):
    trips = await list_user_trips(db, current_user.id, page, page_size)
    response = TripListResponse(
        trips=trips,
        total=len(trips),
        page=page,
        page_size=page_size,
    )
    return response


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # 行程校验
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise NotFoundError()

    # 权限校验
    if trip.user_id != current_user.id:
        raise ForbiddenError()
    return trip


@router.delete("/{trip_id}")
async def remove_trip(
    trip_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise NotFoundError()
    if trip.user_id != current_user.id:
        raise ForbiddenError()
    result = await delete_trip(db, trip_id)
    return result


@router.patch("/{trip_id}", response_model=TripResponse)
async def patch_trip(
    trip_id: int,
    body: TripUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新行程：支持修改 title 或 status（如 draft → confirmed）"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise NotFoundError()
    if trip.user_id != current_user.id:
        raise ForbiddenError()
    updated = await update_trip(
        db,
        trip_id,
        title=body.title,
        status=body.status,
    )
    return updated


@router.get("/{trip_id}/messages", response_model=list[MessageItem])
async def get_messages(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取行程的所有历史对话消息"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise NotFoundError()
    if trip.user_id != current_user.id:
        raise ForbiddenError()
    messages = await get_all_trip_messages(db, trip_id)
    return [MessageItem.model_validate(m) for m in messages]
