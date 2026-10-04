"""Critic 审查闭环 — 从 planner 4.5 段与 _regenerate_plan 抽出的独立模块（纯搬移，行为不变）

自包含：内部完成「审查方案 → 不达标则重生成 → 重生成产物过校验层」，
判定树逻辑与改造前逐字节一致。调用方拿 events 列表收集 thinking 事件，
再决定如何透传；max_regenerate 由调用方传入（本模块不读 settings 的开关）。
"""

import json
import logging

from pydantic import ValidationError

from backend.app import settings
from backend.app.agent.extract_json import extract_plan_json
from backend.app.schemas.plan import PlanData

logger = logging.getLogger(__name__)


async def _ask_critic(
    llm_client, prompt_builder, conversation, plan_data_json: dict, user_input: str
) -> dict | None:
    """构造 Prompt 调用 LLM 开始审查 Json"""
    extra_system = prompt_builder.build_critic_prompt()

    """ 拼接 message """
    messages = [{"role": "system", "content": extra_system}]

    messages.append(
        {
            "role": "user",
            "content": (
                f"用户需求：{user_input}\n"
                f"{prompt_builder.render_preferences(conversation.pref)}\n"
                f"请审查以下行程 JSON：\n"
                f"{json.dumps(plan_data_json, ensure_ascii=False, indent=2)}"
            ),
        }
    )

    """非流式调用LLM + 解析审查结果"""
    # 整个审查调用都可能失败（网络错误 / 返回非 JSON / 字段缺失），
    # 必须 try 包住，失败返回 None → 上层判定树降级用原方案，不阻断主流程
    try:
        response = await llm_client.client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            timeout=settings.LLM_REQUEST_TIMEOUT,
            temperature=0,
            messages=messages,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        passed = result.get("passed")
        scores = result.get("scores", {})
        issues = result.get("issues", [])
        # 防御：LLM 可能自相矛盾（passed=True 但给了修正项），保守按不达标处理，
        # 保证「有 issues 就触发重生成」这一判定树规则不被绕过
        if issues and passed is True:
            passed = False
        if (
            passed is True
            and scores
            and any(v < settings.CRITIC_SCORE_THRESHOLD for v in scores.values())
        ):
            passed = False
            if not issues:
                issues = [
                    f"{dim}维度分数低于{settings.CRITIC_SCORE_THRESHOLD}，请针对性优化"
                    for dim, score in scores.items()
                    if score < settings.CRITIC_SCORE_THRESHOLD
                ]
        if not isinstance(issues, list):
            issues = []
        issues = [str(i) for i in issues][:3]
    except Exception as e:
        logger.warning("审查结果解析失败：%s", e)
        return None

    return {"passed": passed, "scores": scores, "issues": issues}


async def _regenerate_plan(
    llm_client, prompt_builder, conversation, plan_data: dict, user_input: str, issues: list
) -> str:
    """根据审查反馈重生成一版行程方案（轻量单轮流式，服务端累积，不 yield 给前端）。

    输入：
        plan_data   : v1 的行程 JSON dict（审查不达标的那版）
        user_input  : 用户原始需求（重生成时带回去，避免丢初始约束）
        issues      : 审查员给出的修正项列表（如 ["预算超支", "第2天太赶"]）
        conversation: 会话管理器（取 history_cache / pref 拼 prompt）

    返回：
        str —— 重生成的完整文本（含自然语言 + ```json 代码块，调用方再 extract_plan_json 解析）

    设计要点（对齐 _apply_feedback 范式）：
        - 把「v1 行程 JSON + 用户需求 + 逐条 issues」拼进 extra_system
        - 复用 build_messages 拼 messages：带 user_input（初始约束）+ pref（偏好）+ extra_system（修正指令）
        - 走 chat_stream 流式，但只在服务端累积返回，不 yield —— 见 handle_message 说明
    """
    # 1. 把审查反馈（issues 列表）逐条转成 "- 问题" 行，用换行拼接。
    #    f"- {issue}" 逐条加前缀；issues 非空由调用方判定树保证，这里无需判空
    issue_lines = "\n".join(f"- {issue}" for issue in issues)

    # 2. 拼接修正指令：v1 JSON + 用户需求 + 审查问题 + 输出规范（照抄 _apply_feedback 的写法）
    regenerate_prompt = f"""以下是刚生成的行程 JSON：
    {json.dumps(plan_data, ensure_ascii=False, indent=2)}

    用户原始需求：{user_input}

    质量审查发现以下问题，请逐条修正：
    {issue_lines}

    请保持用户原始需求与行程主体不变，只在问题范围内做局部调整。
    先用自然语言简要说明你做了哪些优化，然后在回复末尾用 ```json 代码块返回修正后的完整行程 JSON，字段结构与原 JSON 保持一致，不要省略任何字段。"""

    # 3. 复用 build_messages 拼 messages：
    #    user_input 当 user 消息（初始约束不丢）+ pref 偏好段 + extra_system 修正指令
    messages = prompt_builder.build_messages(
        history=conversation.history_cache,
        user_input=user_input,
        pref=conversation.pref,
        extra_system=regenerate_prompt,
        summary=conversation.summary,
    )

    # 4. 服务端累积流式输出，返回完整文本（不 yield 给前端，理由见 handle_message）
    full_text = ""
    async for chunk in llm_client.chat_stream(messages):
        full_text += chunk
    return full_text


async def run_critic_loop(
    llm_client,
    prompt_builder,
    conversation,
    user_input: str,
    display_text: str,
    plan_data: dict | None,
    max_regenerate: int,
    events: list,
) -> tuple[str, dict | None]:
    """Critic 判定树（原 planner 4.5 段逻辑逐字节照搬）。返回 (display_text, plan_data)。

    - events 是调用方传入的 list，函数内用 events.append({"type": "thinking", "content": ...}) 收集
      thinking 事件（顺序与原文 yield 顺序一致），不直接 yield。
    - 函数不读 settings（max_regenerate 由调用方传入），但 _ask_critic 内部读 settings 取 model/timeout。
    """
    events.append({"type": "thinking", "content": "正在对行程方案做质量审查…"})
    critic_result = await _ask_critic(
        llm_client, prompt_builder, conversation, plan_data, user_input
    )

    # 进入重生成的条件（缺一不可）：
    #   1. critic_result 非空 —— 审查成功（失败降级返回 None，直接用原方案，不阻断主流程）
    #   2. not passed —— 审查不达标
    #   3. issues 非空 —— 审查员给出了可执行的修正项（只有明确了问题才值得再花一次生成）
    if critic_result and not critic_result["passed"] and critic_result["issues"]:
        events.append({"type": "thinking", "content": "审查发现部分安排需要优化，正在重新生成方案"})
        # 重生成循环：最多 max_regenerate 次（默认 1 次），防无限循环烧 token。
        # 每次产出合法 JSON 即采纳；全失败则保持 v1 原方案，流程继续。
        for _ in range(max_regenerate):
            new_text = await _regenerate_plan(
                llm_client,
                prompt_builder,
                conversation,
                plan_data,
                user_input,
                critic_result["issues"],
            )
            new_display, new_plan = extract_plan_json(new_text)
            # 重生成产物同样过校验层，不合格不采纳（保持 v1 原方案）
            if new_plan is not None:
                try:
                    new_plan = PlanData.model_validate(new_plan).model_dump()
                except ValidationError:
                    new_plan = None
            if new_plan is not None:
                display_text, plan_data = new_display, new_plan
                break

    return display_text, plan_data
