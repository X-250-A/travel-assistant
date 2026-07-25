"""
TripResponse, TripCreate, 消息列表响应, 行程更新请求
"""


from datetime import datetime

from pydantic import BaseModel


class TripResponse(BaseModel):
    id: int
    user_id: int
    title: str
    plan_data: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class TripListResponse(BaseModel):
    trips: list[TripResponse]
    total: int
    page: int
    page_size: int

class TripUpdateRequest(BaseModel):
    """行程更新请求 — 只更新传入的字段"""
    title: str | None = None
    status: str | None = None

class MessageItem(BaseModel):
    id: int
    trip_id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}