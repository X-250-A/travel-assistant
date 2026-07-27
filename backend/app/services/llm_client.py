"""
LLMClient: DeepSeek API 封装（重试、超时、流式）
"""

import httpx
from openai import AsyncOpenAI
from backend.app.config import settings


class LLMClient:
    """DeepSeek SDK 封装"""
    def __init__(self):
        # 显式创建不设代理的 httpx 客户端，防止 Windows 系统代理干扰连接
        http_client = httpx.AsyncClient(
            proxy=None,
            trust_env=False,
            timeout=httpx.Timeout(60.0),
        )
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            http_client=http_client,
        )
        self.model = settings.DEEPSEEK_MODEL

    async def chat(self, messages: list[dict], tools : list[dict]):
        kwargs = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        """非流式调用，返回完整响应文本"""
        responses = await self.client.chat.completions.create(**kwargs)

        return responses.choices[0].message

    async def chat_stream(self, messages: list[dict]):
        """流式调用，返回 AsyncGenerator[str]"""
        stream = await self.client.chat.completions.create(
            model=self.model,  # type: ignore
            messages=messages,  # type: ignore
            stream=True, # type: ignore
        )
        async for chunk in stream:  # type: ignore
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


    def count_tokens(self, text: str) -> int:
        """估算 Token 数"""
        return len(text) // 2
