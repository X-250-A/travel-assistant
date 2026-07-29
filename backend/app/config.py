from pathlib import Path
from pydantic_settings import BaseSettings

# 创建一个能从.env文件中读取环境变量的类，方便JWT，LLM的API_KEY等的存放
class Settings(BaseSettings):
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

    # 超时粒度细化
    # LLM 超时（秒）
    LLM_CONNECT_TIMEOUT: float = 10.0  # DNS + TCP + TLS 握手
    LLM_READ_TIMEOUT: float = 45.0  # 等待服务器响应的单次 read 间隔
    LLM_REQUEST_TIMEOUT: float = 90.0  # 整个 API 调用的总时长上限（传给 SDK）

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8"
    }

settings = Settings()