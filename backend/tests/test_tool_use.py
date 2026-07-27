"""
测试 Tool Use：检查 LLM 是否能识别并调用工具
"""
import asyncio
import sys
import io
from pathlib import Path

# 解决 Windows 终端打印 emoji 报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 把项目根目录加入 Python 路径（backend 的父目录）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services.llm_client import LLMClient
from backend.app.tools.weather import WEATHER_TOOL, get_weather


async def test_tool_call():
    """测试 LLM 是否识别天气查询意图并调用 get_weather"""
    client = LLMClient()

    messages = [
        {"role": "system", "content": "你是一个旅游助手，可以通过查天气来回答用户问题。"},
        {"role": "user", "content": "北京今天天气怎么样？适合出去玩吗？"}
    ]

    print("=" * 50)
    print("1. 调用 LLM（非流式，带 tools）...")
    message = await client.chat(messages, [WEATHER_TOOL])

    if message.tool_calls:
        for tc in message.tool_calls:
            print(f"\n2. LLM 调用了工具：{tc.function.name}")
            print(f"   参数：{tc.function.arguments}")

            # 执行工具
            fn_name = tc.function.name
            fn_args = eval(tc.function.arguments)  # 简化，生产环境用 json.loads
            print(f"\n3. 执行 {fn_name}...")
            result = await get_weather(**fn_args)
            print(f"   结果：\n{result}")

            # 把结果回传给 LLM
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        print("\n4. 带着结果再次调 LLM...")
        message2 = await client.chat(messages, [WEATHER_TOOL])
        print(f"   LLM 回复：{message2.content}")

    else:
        print("LLM 没有调用工具，直接回复了：")
        print(message.content)


if __name__ == "__main__":
    asyncio.run(test_tool_call())
