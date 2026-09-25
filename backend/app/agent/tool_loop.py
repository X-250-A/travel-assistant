"""工具调用主循环 — 从 planner._generate_plan 抽出的独立模块（纯搬移，行为不变）

自包含：内部完成「首次 chat → 无 tool_calls 则流式输出 / 有则执行工具→观察→再问」，
直到 LLM 不再要工具（流式输出）或达到 max_round 上限（兜底流式输出）。
调用方只需一个 `async for ... yield` 透传。
"""

import json
from json import JSONDecodeError

from backend.app.logging_config import logger
from backend.app.tools import execute_tool


async def run_tool_loop(llm_client, messages, tool_defs, max_round):
    """工具调用主循环：首次 chat → 无 tool_calls 则流式输出；有则执行工具→观察→再问，
    直到 LLM 不再要工具或达 max_round 上限（兜底流式输出）。

    yield 事件（契约与改造前内联循环逐字节一致）：
      {"type": "thinking", ...}  工具调用预告（透传前端）
      {"type": "token", ...}     chat_stream 逐字输出（拼 full_text + 前端打字机）

    parse_fail_count 是函数局部变量：每次调用重新初始化，失败计数不跨请求累积。
    max_round 由调用方传入（本模块不读 settings，保持纯函数化，便于测试传小值）。
    """
    thoughts: list[str] = []

    # 非流式调用LLM
    message = await llm_client.chat(messages, tool_defs)
    if not message.tool_calls:
        # 没有工具调用的需求，则yield流式输出
        async for chunk in llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}
        return

    parse_fail_count = {}
    tool_round = 0

    while tool_round < max_round:
        tool_round += 1

        messages.append(
            {
                "role": "assistant",
                "content": message.content,  # 可能为 None
                "tool_calls": message.tool_calls,  # tool_calls 列表
            }
        )

        tool_names = ", ".join(tool_call.function.name for tool_call in message.tool_calls)

        yield {"type": "thinking", "content": f"我现在要使用 {tool_names} 工具以确认安排"}

        observations = []

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except (JSONDecodeError, TypeError) as e:
                parse_fail_count[fn_name] = parse_fail_count.get(fn_name, 0) + 1
                logger.warning(
                    "参数解析失败：tool=%s，err=%s, args=%.200s",
                    fn_name,
                    e,
                    tool_call.function.arguments,
                )
                if parse_fail_count[fn_name] >= 2:
                    msg = "参数解析连续失败已达 2 次上限，本工具调用已跳过，请勿再次调用该工具"
                else:
                    msg = "参数解析失败，请修正参数后重新调用该工具，或放弃调用"
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": msg})
                observations.append(f"{fn_name}(解析失败) → {msg}")
                continue

            result = await execute_tool(fn_name, **fn_args)

            observations.append(f"{fn_name}({fn_args}) → {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

        # 在 observations 循环结束、调用下一轮 LLM 之前
        summary = "; ".join(obs[:120] for obs in observations)
        thoughts.append(f"第{tool_round}轮：调用了 {tool_names}，结果：{summary[:150]}")

        messages.append(
            {
                "role": "assistant",
                "content": (
                    "[内部推理] 我目前已掌握的信息：\n"
                    + "\n".join(f"- {t}" for t in thoughts[-3:])
                    + "\n\n请基于以上信息评估：是否已满足用户需求？"
                    "若已满足，直接组织最终行程回答，不要调用工具；"
                    "若关键信息仍有缺失，再调用工具补充。"
                ),
            }
        )

        message = await llm_client.chat(messages, tool_defs)

        if not message.tool_calls:
            async for chunk in llm_client.chat_stream(messages):
                yield {"type": "token", "content": chunk}
            return

    # 调用上限后的兜底处理
    # ← 走到这里说明 max_round 轮工具调用后 LLM 还在要工具
    logger.warning("工具调用超过 %s 轮，强制结束", max_round)
    # 兜底：把当前上下文流式输出
    async for chunk in llm_client.chat_stream(messages):
        yield {"type": "token", "content": chunk}
