"""
JWT Token 工具

封装 python-jose 的 Token 创建和验证逻辑。
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from backend.app import settings

ALGORITHMS = ["HS256"]


# 生成token
def create_access_token(user_id: dict):
    to_encode = user_id.copy()  # 复制原始数据，防止篡改原始数据
    expire_time = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )  # 计算过期时间
    to_encode.update(
        {
            "exp": expire_time,
            "iat": datetime.now(UTC),
            "jti": str(uuid.uuid4()),
        }
    )  # 在传入的数据的复制本中插入exp字段，包含过期时间
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHMS[0])
    return token


# 验证token
def decode_token(token: str):
    """解码并验证token，返回payload字段"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=ALGORITHMS)
        return payload
    except JWTError:
        raise ValueError("无效的token") from None
