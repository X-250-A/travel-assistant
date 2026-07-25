"""
JWT Token 工具

封装 python-jose 的 Token 创建和验证逻辑。
"""
from datetime import datetime, timedelta, timezone

from backend.app.config import settings
from jose import jwt, JWTError


ALGORITHMS = ["HS256"]
ACCESS_TOKEN_EXPIRE_HOURS = 24



# 生成token
def create_access_token(user_id : dict):
    to_encode = user_id.copy() # 复制原始数据，防止篡改原始数据
    expire_time = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS) # 计算过期时间
    to_encode.update({"exp": expire_time}) # 在传入的数据的复制本中插入exp字段，包含过期时间
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHMS[0])
    return token


# 验证token
def decode_token(token: str):
    """解码并验证token，返回payload字段"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=ALGORITHMS)
        return payload
    except JWTError:
        raise ValueError("无效的token")


