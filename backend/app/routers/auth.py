from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.crud import user
from backend.app.schemas.auth import RegisterRequest, LoginRequest, UserResponse, TokenResponse
from backend.app.utils.jwt import create_access_token
from backend.app.routers.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(user_data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await user.find_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    new_user = await user.create_user(db, user_data)
    return UserResponse(username=new_user.username, id=new_user.id)




@router.post("/login", response_model=TokenResponse)
async def login(user_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    existing = await user.authenticate_user(db, user_data.username, user_data.password)
    if not existing:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"user_id": existing.id})
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def me(current_user = Depends(get_current_user)):
    return current_user
