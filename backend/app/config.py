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

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8"
    }

settings = Settings()