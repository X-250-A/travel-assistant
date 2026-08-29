"""
全局依赖注入函数

提供可复用的 Depends 函数：鉴权、权限检查等。
"""


from fastapi import Depends
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import settings
from backend.app.crud import user
from backend.app.db import get_db, get_redis
from backend.app.exceptions import NotFoundError, TooManyRequestsError
from backend.app.ratelimit import check_rate_limit


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.state.user_id
    current_user = await user.find_user_by_id(db, user_id)
    if current_user is None:
        raise NotFoundError(detail="用户不存在")
    return current_user


async def ip_ratelimit(
        request: Request,
):
    ip = request.client.host # 获取用户ip
    # 启动redis
    r = await get_redis()
    ok = await check_rate_limit(r,f"rate:ip:{request.url.path}:{ip}", settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)
    await r.aclose()
    if not ok:
        raise TooManyRequestsError(detail="请求过于频繁，请稍后再试")
    return True
