import httpx
from openai import AsyncOpenAI

from backend.app.config import settings


class EmbeddingClient:
    def __init__(self):
        http_client = httpx.AsyncClient(
            proxy=None,
            trust_env=False,
            timeout=httpx.Timeout(
                connect=settings.LLM_CONNECT_TIMEOUT,
                read=settings.LLM_READ_TIMEOUT,
                write=10.0,
                pool=5.0
            )
        )

        self.client = AsyncOpenAI(
            http_client=http_client,
            base_url=settings.SILICONFLOW_BASE_URL,
            api_key=settings.SILICONFLOW_API_KEY
        )

        self.model = settings.SILICONFLOW_EMBEDDING_MODEL

    # 预备降级处理
    def available(self):
        return "change-me" not in settings.SILICONFLOW_API_KEY

    # 核心embed逻辑
    async def embed(self, text: list[str]):
        resp = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return [item.embedding for item in resp.data]
