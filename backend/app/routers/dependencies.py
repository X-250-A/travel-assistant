"""
全局依赖注入函数

提供可复用的 Depends 函数：鉴权、权限检查等。
"""


from fastapi import Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.crud import user

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.state.user_id
    current_user = await user.find_user_by_id(db, user_id)
    if current_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return current_user
