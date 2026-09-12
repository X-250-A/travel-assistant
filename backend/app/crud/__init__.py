"""crud 注册中心 — 统一导出所有数据库操作函数"""

from backend.app.crud.message import get_all_trip_messages, get_trip_messages, save_message
from backend.app.crud.trip import (
    create_trip,
    delete_trip,
    find_trip_by_id,
    list_user_trips,
    update_trip,
)
from backend.app.crud.user import (
    authenticate_user,
    create_user,
    find_user_by_id,
    find_user_by_username,
)

__all__ = [
    "save_message",
    "get_trip_messages",
    "get_all_trip_messages",
    "create_trip",
    "find_trip_by_id",
    "list_user_trips",
    "update_trip",
    "delete_trip",
    "find_user_by_username",
    "find_user_by_id",
    "authenticate_user",
    "create_user",
]
