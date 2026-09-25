"""tool_loop 测试 — 工具调用主循环（首轮收敛 / 参数解析连续失败跳过 / 超轮兜底）"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agent.tool_loop import run_tool_loop

EXECUTE_TOOL_PATCH = "backend.app.agent.tool_loop.execute_tool"


def _tool_call(name: str, arguments: str, call_id: str = "call_001") -> MagicMock:
    """构造一个假 tool_call（function.name / function.arguments / id）"""
    tool_call = MagicMock()
    tool_call.function.name = name
    tool_call.function.arguments = arguments
    tool_call.id = call_id
    return tool_call


def _message(content, tool_calls) -> MagicMock:
    """构造一个假 LLM 非流式响应（content / tool_calls）"""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    return message


def _stream(chunks: list[str]) -> MagicMock:
    """构造一个可 async for 的假 chat_stream（逐条产出 chunks）"""
    stream = AsyncMock()
    stream.__aiter__.return_value = chunks
    return stream


@pytest.mark.asyncio
async def test_first_round_converges_to_stream():
    """LLM 第一轮要工具、拿到结果后第二轮不再要 → 执行 1 次工具并流式输出 token"""
    tool_msg = _message(None, [_tool_call("get_weather", json.dumps({"city": "北京"}))])
    final_msg = _message("北京今天多云，适合出游。", None)

    llm_client = MagicMock()
    llm_client.chat = AsyncMock(side_effect=[tool_msg, final_msg])
    llm_client.chat_stream = MagicMock(return_value=_stream(["北京", "今天多云，适合出游。"]))

    messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
    with patch(
        EXECUTE_TOOL_PATCH,
        new=AsyncMock(return_value="【北京 当前天气】多云 25°C"),
    ) as mock_execute:
        events = [event async for event in run_tool_loop(llm_client, messages, [], 10)]

    assert llm_client.chat.await_count == 2

    thinking = [e for e in events if e["type"] == "thinking"]
    tokens = [e for e in events if e["type"] == "token"]
    assert thinking, "应产出 thinking 事件"
    assert tokens, "应产出 token 事件"
    # 顺序：thinking 预告在前，chat_stream 的 token 在后
    assert events.index(thinking[0]) < events.index(tokens[0])
    assert "get_weather" in thinking[0]["content"]
    assert [e["content"] for e in tokens] == ["北京", "今天多云，适合出游。"]

    # 工具恰好执行 1 次，参数已从 JSON 解析成 kwargs
    mock_execute.assert_awaited_once_with("get_weather", city="北京")
    # 工具结果按契约回填为 role=tool 的消息
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    assert tool_messages[0]["content"] == "【北京 当前天气】多云 25°C"


@pytest.mark.asyncio
async def test_same_tool_parse_failure_twice_marks_skipped():
    """同一工具参数解析连续失败 2 次 → 第 2 次失败发给 LLM 的 tool 消息标记「已跳过」"""
    tool_msg = _message(None, [_tool_call("get_weather", "not json{")])

    # messages 是同一个 list、被原地追加；每次 chat 调用时留一份快照才能看清「当时发出去的内容」
    chat_snapshots: list[list[dict]] = []

    async def _fake_chat(messages_arg, tool_defs):
        chat_snapshots.append([dict(m) for m in messages_arg])
        return tool_msg

    llm_client = MagicMock()
    llm_client.chat = AsyncMock(side_effect=_fake_chat)
    llm_client.chat_stream = MagicMock(return_value=_stream(["兜底"]))

    messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
    with patch(EXECUTE_TOOL_PATCH, new=AsyncMock(return_value="never")) as mock_execute:
        events = [event async for event in run_tool_loop(llm_client, messages, [], 3)]

    # 参数解析失败 → 工具一次都不能被执行
    mock_execute.assert_not_awaited()

    # 第 3 次 chat（第 2 轮失败后）才带上「已跳过」提示；第 2 次 chat 仍是「请修正参数」
    first_tool_contents = [m["content"] for m in chat_snapshots[1] if m.get("role") == "tool"]
    second_tool_contents = [m["content"] for m in chat_snapshots[2] if m.get("role") == "tool"]

    assert any("请修正参数后重新调用该工具" in c for c in first_tool_contents)
    assert not any("已跳过，请勿再次调用" in c for c in first_tool_contents)
    assert any("已跳过，请勿再次调用该工具" in c for c in second_tool_contents)

    # 每轮都产出 thinking 预告（透传前端），内容含工具名
    assert sum(1 for e in events if e["type"] == "thinking") == 3


@pytest.mark.asyncio
async def test_parse_fail_count_is_local_to_each_call():
    """红线：parse_fail_count 为函数局部变量 —— 失败计数不跨调用累积到下一次生成"""
    tool_msg = _message(None, [_tool_call("get_weather", "not json{")])
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(return_value=tool_msg)
    llm_client.chat_stream = MagicMock(return_value=_stream(["兜底"]))

    with patch(EXECUTE_TOOL_PATCH, new=AsyncMock(return_value="never")):
        # 第一次调用：1 轮（1 次失败），随后是全新一次调用
        [e async for e in run_tool_loop(llm_client, [{"role": "user", "content": "1"}], [], 1)]
        llm_client.chat.reset_mock()
        [e async for e in run_tool_loop(llm_client, [{"role": "user", "content": "2"}], [], 1)]

    # 新一次调用的第一次失败必须是「请修正参数」，而不是「已跳过」
    tool_contents = [
        m["content"] for m in llm_client.chat.await_args.args[0] if m.get("role") == "tool"
    ]
    assert any("请修正参数后重新调用该工具" in c for c in tool_contents)
    assert not any("已跳过" in c for c in tool_contents)


@pytest.mark.asyncio
async def test_max_round_reached_falls_back_to_stream(caplog):
    """LLM 始终要工具 → 达到 max_round 上限后执行恰好 max_round 轮并兜底流式输出"""
    tool_msg = _message(None, [_tool_call("get_weather", json.dumps({"city": "北京"}))])
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(return_value=tool_msg)
    llm_client.chat_stream = MagicMock(return_value=_stream(["兜底", "输出"]))

    messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
    with (
        caplog.at_level(logging.WARNING, logger="app"),
        patch(
            EXECUTE_TOOL_PATCH,
            new=AsyncMock(return_value="【北京 当前天气】多云 25°C"),
        ) as mock_execute,
    ):
        events = [event async for event in run_tool_loop(llm_client, messages, [], 2)]

    # max_round=2 → 工具执行 2 轮后强制结束（chat：首次 + 每轮末尾 = 3 次）
    assert mock_execute.await_count == 2
    assert llm_client.chat.await_count == 3
    assert sum(1 for e in events if e["type"] == "thinking") == 2

    # 兜底走 chat_stream 逐字输出
    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert tokens == ["兜底", "输出"]

    # 触发「超过 n 轮，强制结束」warning 日志
    assert any("工具调用超过 2 轮，强制结束" in r.getMessage() for r in caplog.records)
