"""
JWT 验证中间件，提取 current_user 注入请求上下文
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.app.utils.jwt import decode_token
from starlette import status
from backend.app.config import settings
from backend.app.db.redis import get_redis


PUBLIC_PATHS = frozenset({
    "/",
    "/api/auth/register",
    "/api/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
})



async def jwt_middleware(request: Request, call_next):
    # 白名单路径直接放行
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    # 进入请求的前置逻辑：

    # 获取Authorization验证信息
    authorization = request.headers.get("Authorization")
    # 校验验证信息是否存在
    if not authorization:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "未提供认证信息"})
    # 校验Authorization的"Bearer "格式
    if not authorization.startswith("Bearer "):
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token格式错误"})
    #获取token
    token = authorization.replace("Bearer ", "")

    # 验证并解码token(验证逻辑在decode_token函数中)
    try:
        payload = decode_token(token)
    except:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token无效或已过期"})

    user_id = payload.get("user_id")
    jti = payload.get("jti")

    # 查Redis的token黑名单
    r = await get_redis(settings.REDIS_TOKEN_BLACKLIST_DB)
    is_blacklisted = await r.sismember(f"blacklist:{user_id}", jti)
    await r.close()
    if is_blacklisted:
        return JSONResponse(status_code=status.HTTP_401_FORBIDDEN, content={"detail": "token处于黑名单"})


    # user_id与jti非空校验
    if not user_id:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token数据异常"})

    request.state.user_id = user_id
    request.state.jti = jti


    # JWT鉴权完毕，请求放行
    response = await call_next(request)

    return response
