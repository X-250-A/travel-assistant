from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from starlette import status

from backend.app.models.user import User
from backend.app.routers.dependencies import get_current_user
from backend.app.crud.trip import list_user_trips, find_trip_by_id, delete_trip, update_trip
from backend.app.crud.message import get_all_trip_messages
from backend.app.schemas.trip import TripListResponse, TripUpdateRequest, MessageItem

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("")
async def list_trips(
    db : AsyncSession = Depends(get_db),
    current_user : User = Depends(get_current_user),
    page : int = 1,
    page_size: int = 100
):
    trips = await list_user_trips(db, current_user.id, page, page_size)
    response = TripListResponse(
        trips=trips,
        total=len(trips),
        page=page,
        page_size=page_size,
    )
    return response



@router.get("/{trip_id}")
async def get_trip(
    trip_id: int,
    db : AsyncSession = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    # 行程校验
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    # 权限校验
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return trip


@router.delete("/{trip_id}")
async def remove_trip(
    trip_id: int,
    db : AsyncSession = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = await delete_trip(db,trip_id)
    return result


@router.patch("/{trip_id}")
async def patch_trip(
    trip_id: int,
    body: TripUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新行程：支持修改 title 或 status（如 draft → confirmed）"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    updated = await update_trip(
        db,
        trip_id,
        title=body.title,
        status=body.status,
    )
    return updated


@router.get("/{trip_id}/messages")
async def get_messages(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取行程的所有历史对话消息"""
    trip = await find_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    messages = await get_all_trip_messages(db, trip_id)
    return [MessageItem.model_validate(m) for m in messages]

