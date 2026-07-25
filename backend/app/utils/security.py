"""
密码哈希与校验工具

封装 bcrypt 的哈希生成和密码验证逻辑。
"""

import bcrypt


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希，返回字符串形式的哈希值"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码是否与 bcrypt 哈希匹配"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
