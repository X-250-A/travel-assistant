"""
RegisterRequest, LoginRequest, TokenResponse
"""
from pydantic import BaseModel


# 用于注册的响应模型
class RegisterRequest(BaseModel):
    username: str
    password: str


"""
    由于注册和登录在未来所需的字段可能不一致，所以这里新创建一个用于登录的模型类，保留拓展性
"""


#  用于登录的响应模型
class LoginRequest(BaseModel):
    username: str
    password: str


# 用于响应查询用户信息的，传给前端的响应模型
class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {
        "from_attributes": True
    }


# 登录响应模型
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
