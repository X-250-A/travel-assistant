"""
LLMClient: DeepSeek API 封装（重试、超时、流式）
"""

import httpx
import tiktoken
from backend.app.config import settings
from backend.app.services import mock_llm
from openai import AsyncOpenAI


class LLMClient:
    """DeepSeek SDK 封装"""
    def __init__(self):
        # E2E mock 模式：不建真实连接，client 换成内存假实现（意图分类/Critic 直接调 client.chat）
        if settings.LLM_PROVIDER == "mock":
            self.client = mock_llm.MockOpenAIClient()
            self.model = settings.DEEPSEEK_MODEL
            self._encoding = tiktoken.get_encoding("cl100k_base")
            return
        # 显式创建不设代理的 httpx 客户端，防止 Windows 系统代理干扰连接
        http_client = httpx.AsyncClient(
            proxy=None,
            trust_env=False,
            timeout=httpx.Timeout(
                connect=settings.LLM_CONNECT_TIMEOUT,
                read=settings.LLM_READ_TIMEOUT,
                write=10.0,
                pool=5.0
            ),
        )
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            http_client=http_client,
        )
        self.model = settings.DEEPSEEK_MODEL
        self._encoding = tiktoken.get_encoding("cl100k_base")

    async def chat(self, messages: list[dict], tools : list[dict]):
        """非流式调用，返回完整响应文本"""
        if settings.LLM_PROVIDER == "mock":
            return mock_llm.mock_chat(messages, tools)
        kwargs = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": messages,
            "timeout": settings.LLM_REQUEST_TIMEOUT,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"


        responses = await self.client.chat.completions.create(**kwargs)

        return responses.choices[0].message

    async def chat_stream(self, messages: list[dict]):
        """流式调用，返回 AsyncGenerator[str]"""
        if settings.LLM_PROVIDER == "mock":
            async for chunk in mock_llm.mock_chat_stream(messages):
                yield chunk
            return
        stream = await self.client.chat.completions.create(
            model=self.model,  # type: ignore
            messages=messages,  # type: ignore
            stream=True, # type: ignore
            timeout=settings.LLM_REQUEST_TIMEOUT
        )
        async for chunk in stream:  # type: ignore
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


    def count_tokens(self, text: str) -> int:
        """估算 Token 数"""
        return len(self._encoding.encode(text))

