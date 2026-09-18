"""schemas 注册中心 — 统一导出所有 Pydantic 模型"""

from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.schemas.chat import ChatRequest, DoneEvent, ErrorEvent, PlanEvent, TokenEvent
from backend.app.schemas.plan import Attraction, DayPlan, Meal, PlanData
from backend.app.schemas.trip import MessageItem, TripListResponse, TripResponse, TripUpdateRequest

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "TokenResponse",
    "ChatRequest",
    "TokenEvent",
    "PlanEvent",
    "ErrorEvent",
    "DoneEvent",
    "TripResponse",
    "TripListResponse",
    "TripUpdateRequest",
    "MessageItem",
    "PlanData",
    "DayPlan",
    "Attraction",
    "Meal",
]
