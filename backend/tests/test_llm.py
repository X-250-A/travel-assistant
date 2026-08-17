"""快速测试 LLM API 能否调通

依赖外部网络（DeepSeek API），在 CI 环境中默认跳过。
"""

import asyncio

import pytest
from backend.app.services.llm_client import LLMClient

pytestmark = pytest.mark.skip(
    reason="依赖外部 DeepSeek API，开发时用 python -m backend.tests.test_llm 手动运行"
)


async def test_chat():
    """测试非流式调用"""
    client = LLMClient()
    messages = [
        {"role": "system", "content": "你是一个旅游助手"},
        {"role": "user", "content": "你好，请用一句话介绍北京"},
    ]

    print("=== 测试非流式调用 ===")
    reply = await client.chat(messages)
    print(f"回复：{reply}\n")


async def test_chat_stream():
    """测试流式调用"""
    client = LLMClient()
    messages = [
        {"role": "system", "content": "你是一个旅游助手"},
        {"role": "user", "content": "你好，用一句话介绍成都"},
    ]

    print("=== 测试流式调用 ===")
    full_text = ""
    async for chunk in client.chat_stream(messages):
        print(chunk, end="", flush=True)
        full_text += chunk
    print(f"\n（共收到 {len(full_text)} 字符）\n")


def test_count_tokens():
    """测试 Token 估算"""
    client = LLMClient()
    text = "你好，请用一句话介绍北京"
    count = client.count_tokens(text)
    print("=== 测试 Token 估算 ===")
    print(f"原文：{text}")
    print(f"估算 Token 数：{count}")
    print(f"字符数：{len(text)}\n")


async def main():
    await test_chat()
    await test_chat_stream()
    test_count_tokens()
    print("全部测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
