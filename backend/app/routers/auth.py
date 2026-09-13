from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import settings
from backend.app.crud import user
from backend.app.db import get_db, get_redis
from backend.app.exceptions import BadRequestError, UnauthorizedError
from backend.app.routers.dependencies import get_current_user, ip_ratelimit
from backend.app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.utils import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    rate: bool = Depends(ip_ratelimit),
):
    existing = await user.find_user_by_username(db, user_data.username)
    if existing:
        raise BadRequestError(detail="用户名已存在")
    new_user = await user.create_user(db, user_data)
    return UserResponse(username=new_user.username, id=new_user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    user_data: LoginRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    rate: bool = Depends(ip_ratelimit),
):
    # IP限流防批量注册登录

    existing = await user.authenticate_user(db, user_data.username, user_data.password)
    if not existing:
        raise UnauthorizedError(detail="用户名或密码错误")
    token = create_access_token({"user_id": existing.id})
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(request: Request):
    user_id = request.state.user_id
    jti = request.state.jti

    r = await get_redis(settings.REDIS_TOKEN_BLACKLIST_DB)
    await r.sadd(f"blacklist:{user_id}", jti)
    await r.expire(f"blacklist:{user_id}", settings.ACCESS_TOKEN_EXPIRE_MINUTES + 3600)
    await r.aclose()

    return {"message": "logout_success"}
