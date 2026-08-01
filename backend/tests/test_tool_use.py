"""
测试 Tool Use：验证 LLM 识别工具意图 → 执行工具 → 回传结果的完整循环
"""
import asyncio
import json
import sys
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 解决 Windows 终端打印 emoji 报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 把项目根目录加入 Python 路径（backend 的父目录）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services import llm_client as llm_client_module
from backend.app.tools.weather import weather_tool
from backend.app.tools import weather as weather_module


async def test_tool_call():
    """验证 LLM 返回 tool_call 后能正确执行 get_weather 并回传结果"""
    # 第一次 chat() → 返回带 tool_call 的消息（LLM 决定查天气）
    tool_call = MagicMock()
    tool_call.function.name = "get_weather"
    tool_call.function.arguments = json.dumps({"city": "北京"})
    tool_call.id = "call_001"

    tool_msg = MagicMock()
    tool_msg.content = None
    tool_msg.tool_calls = [tool_call]

    # 第二次 chat() → 拿到工具结果后返回最终回复
    final_msg = MagicMock()
    final_msg.content = "北京今天多云转晴，很适合出游。"
    final_msg.tool_calls = None

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(side_effect=[tool_msg, final_msg])

    # LLMClient 依赖 DeepSeek API、get_weather 依赖外部天气 API，测试中用 mock 替换
    with (
        patch.object(llm_client_module, "LLMClient", return_value=mock_llm),
        patch.object(weather_module, "get_weather", return_value="【北京 当前天气】多云 25°C"),
    ):
        client = llm_client_module.LLMClient()
        messages = [
            {"role": "system", "content": "你是一个旅游助手，可以通过查天气来回答用户问题。"},
            {"role": "user", "content": "北京今天天气怎么样？适合出去玩吗？"}
        ]

        # 1. 首次调用：LLM 识别出查天气意图，返回工具调用
        message = await client.chat(messages, [weather_tool.openai_schema()])
        assert message.tool_calls
        assert message.tool_calls[0].function.name == "get_weather"

        # 2. 执行工具
        fn_args = json.loads(message.tool_calls[0].function.arguments)
        result = await weather_module.get_weather(**fn_args)
        assert "北京" in result

        # 3. 回传工具结果
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": message.tool_calls,
        })
        messages.append({
            "role": "tool",
            "tool_call_id": message.tool_calls[0].id,
            "content": result,
        })

        # 4. 带着结果再次调用：LLM 生成最终回复
        message2 = await client.chat(messages, [weather_tool.openai_schema()])
        assert "出游" in message2.content


if __name__ == "__main__":
    asyncio.run(test_tool_call())
