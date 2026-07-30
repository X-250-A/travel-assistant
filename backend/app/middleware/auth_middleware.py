"""
JWT 验证中间件，提取 current_user 注入请求上下文
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.app.utils.jwt import decode_token
from starlette import status


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
    authorization = request.headers.get("Authorization")
    if not authorization:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "未提供认证信息"})
    if not authorization.startswith("Bearer "):
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token格式错误"})
    token = authorization.replace("Bearer ", "")

    try:
        payload = decode_token(token)
    except:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token无效或已过期"})

    user_id = payload.get("user_id")
    if not user_id:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "token数据异常"})

    request.state.user_id = user_id

    response = await call_next(request)

    return response
