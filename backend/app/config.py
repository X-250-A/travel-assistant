from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings


# 创建能从 .env 文件读取环境变量的类，方便 JWT / LLM 的 API_KEY 等存放

# ── 必须真实配置的关键字段 ──
# 这些字段既不能是默认占位符，也不能是空值，否则服务启动即报错。
# 占位符标记：唯一真源。embedding.py / poi.py / transport_guiding.py 也复用此常量
# 判断某 key 是否仍是未配置的默认占位符（跨模块共享，勿再硬编码 "change-me"）。
PLACEHOLDER_MARKER = "change-me"
_REQUIRED_KEYS = ("SECRET_KEY", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL")


class Settings(BaseSettings):
    @model_validator(mode="after")
    def _validate_required_keys(self):
        """配置校验（两层，先判占位符再判空值）。

        1. 占位符校验：值仍包含默认的 {PLACEHOLDER_MARKER!r} 标记
           → 说明开发者没把 .env 里的默认值替换成真实配置。
        2. 空值校验：值为空字符串或纯空白
           → 说明配置缺失（写成了 "" 或只有空格）。
        """
        placeholders: list[str] = []
        empties: list[str] = []
        for key in _REQUIRED_KEYS:
            value = getattr(self, key, "")
            stripped = (value or "").strip()
            if PLACEHOLDER_MARKER in value:
                placeholders.append(key)
            elif not stripped:
                empties.append(key)

        if placeholders:
            raise ValueError(
                f"以下配置仍是默认占位符，请在.env中替换为真实值：{', '.join(placeholders)}"
            )
        if empties:
            raise ValueError(f"以下配置为空值，请在.env中填写：{', '.join(empties)}")
        return self

    # JWT
    SECRET_KEY: str = f"{PLACEHOLDER_MARKER}-to-a-secret-key"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./trip_agent.db"

    # Deepseek
    DEEPSEEK_API_KEY: str = f"{PLACEHOLDER_MARKER}-to-a-deepseeek-api-key"
    DEEPSEEK_BASE_URL: str = f"{PLACEHOLDER_MARKER}-to-a-deepseeek-base-url"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # LLM 提供方：deepseek（真实调用）/ mock（E2E 测试专用，返回预设响应）
    LLM_PROVIDER: str = "deepseek"

    # weather_tool
    WEATHER_API_KEY: str = f"{PLACEHOLDER_MARKER}-to-a-weather-api-key"

    # transport_guiding
    AMAP_API_KEY: str = f"{PLACEHOLDER_MARKER}-to-a-amap-api-key"

    # 超时粒度细化
    # LLM 超时（秒）
    LLM_CONNECT_TIMEOUT: float = 10.0  # DNS + TCP + TLS 握手
    LLM_READ_TIMEOUT: float = 45.0  # 等待服务器响应的单次 read 间隔
    LLM_REQUEST_TIMEOUT: float = 90.0  # 整个 API 调用的总时长上限（传给 SDK）

    # Redis
    REDIS_URL: str = "redis://192.168.126.128:6379/0"  # 默认开发地址
    REDIS_TOKEN_BLACKLIST_DB: int = 1  # Token 黑名单用独立 DB
    RATE_LIMIT_REQUESTS: int = 30  # 每分钟最大请求数
    RATE_LIMIT_WINDOW: int = 60  # 滑动窗口（秒）

    # token过期时间
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时

    WEATHER_CACHE_TTL: int = 3600  # 1 小时

    PERMANENT_SESSION_LIFETIME: int = 60 * 60 * 24 * 30

    # Critic 行程质量审查（v0.8.0）
    CRITIC_ENABLED: bool = True  # 总开关：对新建/修改的行程方案做第二轮质量审查
    CRITIC_MAX_REGENERATE: int = 1  # 审查不达标时的最大重生成次数（防无限循环）

    # SiliconFlow（向量记忆 embedding，可降级：无 key 时不启用）
    SILICONFLOW_API_KEY: str = f"{PLACEHOLDER_MARKER}-to-a-siliconflow-api-key"
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # 向量记忆
    MEMORY_TOPK: int = 3
    MEMORY_SIM_THRESHOLD: float = 0.45

    # POI 工具
    POI_CACHE_TTL: int = 86400

    # LOGGING调试体系
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
