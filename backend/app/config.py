from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

# 创建一个能从.env文件中读取环境变量的类，方便JWT，LLM的API_KEY等的存放
class Settings(BaseSettings):

    @model_validator(mode="after")
    def _check_required_keys(self):
        critical = [
            "SECRET_KEY",
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
        ]
        missing = [f for f in critical if "change-me" in getattr(self, f, "")]
        if missing:
            raise ValueError(f"请在.env中配置：{', '.join(missing)}")
        return self


    # JWT
    SECRET_KEY: str = "change-me-to-a-secret-key"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./trip_agent.db"

    # Deepseek
    DEEPSEEK_API_KEY: str = "change-me-to-a-deepseeek-api-key"
    DEEPSEEK_BASE_URL: str = "change-me-to-a-deepseeek-base-url"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # weather_tool
    WEATHER_API_KEY: str = "change-me-to-a-weather-api-key"

    # transport_guiding
    AMAP_API_KEY: str = "change-me-to-a-amap-api-key"

    # 超时粒度细化
    # LLM 超时（秒）
    LLM_CONNECT_TIMEOUT: float = 10.0  # DNS + TCP + TLS 握手
    LLM_READ_TIMEOUT: float = 45.0  # 等待服务器响应的单次 read 间隔
    LLM_REQUEST_TIMEOUT: float = 90.0  # 整个 API 调用的总时长上限（传给 SDK）

    REDIS_URL: str = "redis://192.168.126.128:6379/0"  # 默认开发地址
    REDIS_TOKEN_BLACKLIST_DB: int = 1  # Token 黑名单用独立 DB
    RATE_LIMIT_REQUESTS: int = 30  # 每分钟最大请求数
    RATE_LIMIT_WINDOW: int = 60  # 滑动窗口（秒）

    # token过期时间
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时

    WEATHER_CACHE_TTL: int = 3600 # 1 小时

    PERMANENT_SESSION_LIFETIME: int = 60 * 60 * 24 * 30

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8"
    }

settings = Settings()