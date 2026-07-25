"""
全局依赖注入函数

提供可复用的 Depends 函数：鉴权、权限检查等。
"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.crud import user
from backend.app.utils.jwt import decode_token


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(..., description="Bearer <token>"),
):
    """从请求头提取 JWT，解码验证后返回当前用户"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效认证信息")

    token = authorization.removeprefix("Bearer ")

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="token无效或已过期")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="数据异常")

    current_user = await user.find_user_by_id(db, user_id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    return current_user
