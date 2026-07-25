"""
User CRUD 操作

提供 User 模型的增删改查函数，统一收口所有数据库操作。
"""
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.schemas.auth import RegisterRequest
from sqlalchemy import select
from backend.app.utils.security import hash_password, verify_password

# 通过用户名查找用户
async def find_user_by_username(db: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# 通过用户id查找用户
async def find_user_by_id(db: AsyncSession, user_id: int):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

# 校验用户
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await find_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


# 创建用户
async def create_user(db: AsyncSession, user_data: RegisterRequest):
    hashed_password = hash_password(user_data.password) # 哈希加密
    user = User(
        username=user_data.username,
        password=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


