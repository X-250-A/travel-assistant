"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""

import json
from json import JSONDecodeError

from pydantic import ValidationError
from redis.asyncio import Redis

from backend.app import settings
from backend.app.agent import ConversationManager
from backend.app.agent.critic import CriticReviewer
from backend.app.agent.extract_json import PlanJSONExtractor
from backend.app.agent.intent_classifier import IntentClassifier
from backend.app.crud import find_trip_by_id, update_trip
from backend.app.logging_config import logger
from backend.app.memory import (
    Preferences,
    extract_preferences,
    load_preferences,
    recall_vector_memory,
    save_preferences,
    save_vector_memory,
)
from backend.app.schemas.plan import PlanData
from backend.app.services import EmbeddingClient, LLMClient, PromptBuilder
from backend.app.tools import execute_tool, get_tool_schema

MAX_TOOL_ROUND = 10


class TripPlannerAgent(PlanJSONExtractor, IntentClassifier, CriticReviewer):
    """行程规划 Agent 核心"""

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()
        self.embedding_client = EmbeddingClient()

    async def handle_message(self, user_input: str, conversation: ConversationManager, r: Redis):
        """Agent 主入口：接收用户消息，返回 Agent 回复（流式）"""
        conversation.pref = await load_preferences(r, conversation.user_id)

        # 0.记忆召回
        if self.embedding_client.available():
            try:
                history_text = "\n".join(
                    f"{m['role']}: {m['content']}" for m in conversation.history_cache[-6:]
                )
                prompt = self.prompt_builder.build_query_rewrite_prompt(user_input, history_text)
                response = await self.llm_client.client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "system", "content": prompt}],
                    stream=False,
                    temperature=0,
                    response_format={"type": "json_object"},
                    timeout=settings.LLM_REQUEST_TIMEOUT,
                )
                result = json.loads(response.choices[0].message.content)
                query_text = result["rewritten_query"] if result["need_rewrite"] else user_input
            except Exception as e:
                logger.warning("query 改写失败，回退原句：%s", e)
                query_text = user_input

            query_vector = (await self.embedding_client.embed([query_text]))[0]
            memories = await recall_vector_memory(
                r,
                conversation.user_id,
                query_vector,
                settings.MEMORY_TOPK,
                settings.MEMORY_SIM_THRESHOLD,
            )
            conversation.memories = memories or []

        # 1. 保存用户消息
        await conversation.add_message("user", user_input)

        # 1.5 向量记忆保存（提前到意图判断前：所有分支都会走到，含闲聊早退路径）
        await self._save_memory(user_input, conversation, r)

        # 2. 意图判断及分支选择
        intent = await self.llm_classify_intent(user_input, conversation)

        if intent == "new_trip":
            stream = self._generate_plan(conversation)
        elif intent == "modify_trip":
            # 将历史上下文注入缓存
            await conversation.get_context(
                max_tokens=30000, token_counter=self.llm_client.count_tokens
            )
            # 找到对应行程才能修改
            trip = await find_trip_by_id(conversation.db, conversation.trip_id)
            if trip is None:
                yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
                return
            if trip.plan_data is None:
                yield {"type": "token", "content": "当前还没有行程方案，我先帮你规划一个吧！\n"}
                stream = self._generate_plan(conversation)
            else:
                stream = self._apply_feedback(user_input, trip.plan_data, conversation)
        elif intent == "ask_question":
            async for chunk in self.gossip(conversation):
                yield chunk
            return
        else:
            yield {
                "type": "token",
                "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？",
            }
            yield {"type": "done", "data": {}}
            return

        # 3. 消费流式生成器，按事件类型分流：
        #    - token 事件 → 拼进 full_text，同时转发给前端（打字机）
        #    - thinking/tool 事件 → 原样透传，不进入消息文本
        full_text = ""
        async for chunk in stream:
            if chunk["type"] == "token":
                full_text += chunk["content"]
                yield {"type": "token", "content": chunk["content"]}
            else:
                yield chunk

        # 4. 从回复中分离自然语言文本与结构化 JSON
        display_text, plan_data = self._extract_plan_json(full_text)

        # 4.3 校验层（PlanData 校验模型）—— LLM 输出的 JSON 必须通过结构校验才算合法方案
        # 校验失败 → 降级为无方案（plan_data=None），走既有兜底路径：
        # 不存库，前端显示"票面尚未打印"，下次修改行程会触发重新生成
        if plan_data is not None:
            try:
                plan_data = PlanData.model_validate(plan_data).model_dump()
            except ValidationError as e:
                logger.warning("行程 JSON 校验未通过，降级为无方案：%s", e.errors()[:3])
                plan_data = None

        # 4.5 Critic 质量审查（v0.8.0）—— 判定树
        # 审查条件（两个都要满足）：
        #   1. settings.CRITIC_ENABLED —— 总开关开启（测试环境用 env 关掉，避免真打 DeepSeek）
        #   2. plan_data is not None   —— 有方案才审（没解析出合法 JSON 则无可审对象）
        if plan_data is not None and settings.CRITIC_ENABLED:
            yield {"type": "thinking", "content": "正在对行程方案做质量审查…"}
            critic_result = await self._ask_critic(
                user_input=user_input, conversation=conversation, plan_data_json=plan_data
            )

            # 进入重生成的条件（缺一不可）：
            #   1. critic_result 非空 —— 审查成功（失败降级返回 None，直接用原方案，不阻断主流程）
            #   2. not passed —— 审查不达标
            #   3. issues 非空 —— 审查员给出了可执行的修正项（只有明确了问题才值得再花一次生成）
            if critic_result and not critic_result["passed"] and critic_result["issues"]:
                yield {"type": "thinking", "content": "审查发现部分安排需要优化，正在重新生成方案"}
                # 重生成循环：最多 CRITIC_MAX_REGENERATE 次（默认 1 次），防无限循环烧 token。
                # 每次产出合法 JSON 即采纳；全失败则保持 v1 原方案，流程继续。
                for _ in range(settings.CRITIC_MAX_REGENERATE):
                    new_text = await self._regenerate_plan(
                        plan_data=plan_data,
                        user_input=user_input,
                        issues=critic_result["issues"],
                        conversation=conversation,
                    )
                    new_display, new_plan = self._extract_plan_json(new_text)
                    # 重生成产物同样过校验层，不合格不采纳（保持 v1 原方案）
                    if new_plan is not None:
                        try:
                            new_plan = PlanData.model_validate(new_plan).model_dump()
                        except ValidationError:
                            new_plan = None
                    if new_plan is not None:
                        display_text, plan_data = new_display, new_plan
                        break

        # 5. 保存解析出的行程数据
        if plan_data is not None:
            try:
                await update_trip(conversation.db, conversation.trip_id, plan_data=plan_data)

            except Exception as e:
                logger.error("保存行程失败：%s", e)

        # 6. 保存 AI 回复（自然语言部分，不含 JSON 代码块）
        await conversation.add_message("assistant", display_text)

        # 6.5. 保存pref
        try:
            prompt = self.prompt_builder.build_pref_extract_prompt(user_input)
            response = await self.llm_client.client.chat.completions.create(
                messages=[{"role": "system", "content": prompt}],
                stream=False,
                temperature=0,
                response_format={"type": "json_object"},
                model=settings.DEEPSEEK_MODEL,
            )
            data = json.loads(response.choices[0].message.content)
            if data["should_save"]:
                prefs = [Preferences(type=p["type"], value=p["value"]) for p in data["prefs"]]
                await save_preferences(r, conversation.user_id, prefs)

        except Exception as e:
            logger.warning("LLM提取失败：%s", e)
            new_pref = extract_preferences(user_input)
            if new_pref:
                await save_preferences(r, conversation.user_id, new_pref)

        # 7. 结束 — 把 trip_id 带回前端，让前端知道"刚聊的是哪个行程"
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}

    async def _save_memory(self, user_input: str, conversation, r: Redis):
        """LLM 提取可跨会话复用的非结构化记忆 → embed → 写 Redis。全程降级，失败不阻塞"""
        if not self.embedding_client.available():
            return
        try:
            # ① 提取：复刻 llm_classify_intent 的 prompt 组装
            prompt = self.prompt_builder.build_memory_extract_prompt(user_input)
            message = [{"role": "system", "content": prompt}]
            result = await self.llm_client.chat(message, tools=None)  # tools=None 对齐意图识别
            data = json.loads(result.content)  # content 是返回文本
            facts = data.get("facts", [])
            if not data.get("should_save") or not facts:
                return
            # ② embed 全部 facts（一次批量）
            vecs = await self.embedding_client.embed(facts)
            # ③ zip 配对，逐条存
            for fact, vec in zip(facts, vecs, strict=False):
                await save_vector_memory(r, conversation.user_id, fact, vec)
        except Exception as e:
            logger.warning("向量记忆保存失败，跳过：%s", e)

    async def _generate_plan(self, conversation, tool_defs=None):
        """构造 Prompt 调用 LLM 生成行程"""
        context = await conversation.get_context(
            max_tokens=30000, token_counter=self.llm_client.count_tokens
        )

        if not context:
            yield {
                "type": "token",
                "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？",
            }
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref,
            memories=conversation.memories,
        )

        if tool_defs is None:
            tool_defs = get_tool_schema()

        thoughts: list[str] = []

        # 非流式调用LLM
        message = await self.llm_client.chat(messages, tool_defs)
        if not message.tool_calls:
            # 没有工具调用的需求，则yield流式输出
            async for chunk in self.llm_client.chat_stream(messages):
                yield {"type": "token", "content": chunk}
            return

        parse_fail_count = {}
        tool_round = 0

        while tool_round < MAX_TOOL_ROUND:
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

            message = await self.llm_client.chat(messages, tool_defs)

            if not message.tool_calls:
                async for chunk in self.llm_client.chat_stream(messages):
                    yield {"type": "token", "content": chunk}
                return

        # 调用上限后的兜底处理
        # ← 走到这里说明 10 轮工具调用后 LLM 还在要工具
        logger.warning("工具调用超过 %s 轮，强制结束", MAX_TOOL_ROUND)
        # 兜底：把当前上下文流式输出
        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

    async def _regenerate_plan(self, plan_data: dict, user_input: str, issues: list, conversation):
        """根据审查反馈重生成一版行程方案（轻量单轮流式，服务端累积，不 yield 给前端）。

        输入：
            plan_data   : v1 的行程 JSON dict（审查不达标的那版）
            user_input  : 用户原始需求（重生成时带回去，避免丢初始约束）
            issues      : 审查员给出的修正项列表（如 ["预算超支", "第2天太赶"]）
            conversation: 会话管理器（取 history_cache / pref 拼 prompt）

        返回：
            str —— 重生成的完整文本（含自然语言 + ```json 代码块，调用方再 _extract_plan_json 解析）

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
        messages = self.prompt_builder.build_messages(
            history=conversation.history_cache,
            user_input=user_input,
            pref=conversation.pref,
            extra_system=regenerate_prompt,
        )

        # 4. 服务端累积流式输出，返回完整文本（不 yield 给前端，理由见 handle_message）
        full_text = ""
        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
        return full_text

    async def _apply_feedback(self, feedback: str, current_plan: dict, conversation):
        """根据用户反馈调整现有行程"""
        modify_prompt = f"""以下是当前行程的完整 JSON：
        {json.dumps(current_plan, ensure_ascii=False, indent=2)}

        用户要求：{feedback}

        请在现有行程基础上做局部调整。只修改用户提到的部分，其余保持不变。
        先用自然语言说明你做了哪些调整，然后在回复末尾用 ```json 代码块返回修改后的完整行程 JSON。"""
        # 保留原始 system prompt 的角色定义，再追加修改指令

        messages = self.prompt_builder.build_messages(
            history=conversation.history_cache,
            user_input=feedback,
            pref=conversation.pref,
            extra_system=modify_prompt,
        )

        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

    async def gossip(self, conversation):
        context = await conversation.get_context(
            max_tokens=30000, token_counter=self.llm_client.count_tokens
        )

        if not context:
            yield {
                "type": "token",
                "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？",
            }
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref,
            memories=conversation.memories,
        )

        full_text = ""

        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
            yield {"type": "token", "content": chunk}

        await conversation.add_message("assistant", full_text)
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
