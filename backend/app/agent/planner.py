"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""

import json

from pydantic import ValidationError
from redis.asyncio import Redis

from backend.app import settings
from backend.app.agent import ConversationManager, ConversationState
from backend.app.agent.critic import run_critic_loop
from backend.app.agent.extract_json import PlanJSONExtractor
from backend.app.agent.intent_classifier import IntentClassifier
from backend.app.agent.tool_loop import run_tool_loop
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
from backend.app.tools import get_tool_schema


class TripPlannerAgent(PlanJSONExtractor, IntentClassifier):
    """行程规划 Agent 核心"""

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient.get_instance()
        self.embedding_client = EmbeddingClient.get_instance()

    async def handle_message(self, user_input: str, conversation: ConversationManager, r: Redis):
        """Agent 主入口：接收用户消息，返回 Agent 回复（流式）"""
        trip = await find_trip_by_id(conversation.db, conversation.trip_id)
        conversation.sync_state(trip)
        conversation.summary = trip.summary if trip else None
        conversation.pref = await load_preferences(r, conversation.user_id)

        # 0.记忆召回
        if self.embedding_client.available():
            try:
                history_text = "\n".join(
                    f"{m['role']}: {m['content']}" for m in conversation.history_cache[-6:]
                )
                query_prompt = self.prompt_builder.build_query_rewrite_prompt(
                    user_input, history_text
                )
                response = await self.llm_client.client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "system", "content": query_prompt}],
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
                max_tokens=settings.CONTEXT_WINDOW_MAX_TOKENS,
                token_counter=self.llm_client.count_tokens,
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
        elif intent == "confirm":
            if trip is None or trip.plan_data is None:
                yield {"type": "token", "content": "还没有行程方案可以确认，我先帮你规划一个吧！"}
                yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
                return
            await update_trip(conversation.db, conversation.trip_id, status="confirmed")
            conversation.state = ConversationState.DONE
            yield {"type": "token", "content": "好的，行程已确认！"}
            yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
            return

        elif intent == "ask_question":
            async for chunk in self.gossip(conversation):
                yield chunk
            return
        else:
            if len(conversation.history_cache) > 1:
                stream = self._generate_plan(conversation)
                async for chunk in stream:
                    yield chunk
                return
            else:
                yield {
                    "type": "token",
                    "content": "收到，我在这儿～您是想规划一次旅行吗？跟我聊聊目的地、几天、大概预算，我来给您出方案",
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

        # 4.5 Critic 质量审查（v0.8.0）—— 判定树已搬入 critic.run_critic_loop
        # 审查条件（两个都要满足）：
        #   1. settings.CRITIC_ENABLED —— 总开关开启（测试环境用 env 关掉，避免真打 DeepSeek）
        #   2. plan_data is not None   —— 有方案才审（没解析出合法 JSON 则无可审对象）
        if plan_data is not None and settings.CRITIC_ENABLED:
            critic_events: list = []
            display_text, plan_data = await run_critic_loop(
                self.llm_client,
                self.prompt_builder,
                conversation,
                user_input,
                display_text,
                plan_data,
                settings.CRITIC_MAX_REGENERATE,
                critic_events,
            )
            for ev in critic_events:
                yield ev

        # 5. 保存解析出的行程数据
        if plan_data is not None:
            try:
                await update_trip(
                    conversation.db, conversation.trip_id, plan_data=plan_data, status="draft"
                )
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

    async def update_summary(self, conversation):
        if not conversation.old_messages:
            return
        evicted_messages = "\n".join(
            [f"{m['role']}: {m['content']}" for m in conversation.old_messages]
        )
        trip = await find_trip_by_id(db=conversation.db, trip_id=conversation.trip_id)
        try:
            old_summary = trip.summary if trip.summary else ""
            prompt = self.prompt_builder.build_summary_prompt(old_summary, evicted_messages)
            response = await self.llm_client.client.chat.completions.create(
                messages=[{"role": "system", "content": prompt}],
                stream=False,
                model=settings.DEEPSEEK_MODEL,
                temperature=0,
            )
            msg = response.choices[0].message.content
            new_summary = msg.strip()
            await update_trip(db=conversation.db, trip_id=conversation.trip_id, summary=new_summary)
            conversation.summary = new_summary
        except Exception as e:
            logger.warning("摘要失败，跳过：%s", e)

    async def _generate_plan(self, conversation, tool_defs=None):
        """构造 Prompt 调用 LLM 生成行程"""
        context = await conversation.get_context(
            max_tokens=settings.CONTEXT_WINDOW_MAX_TOKENS,
            token_counter=self.llm_client.count_tokens,
        )

        if not context:
            yield {
                "type": "token",
                "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？",
            }
            return

        await self.update_summary(conversation)

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref,
            memories=conversation.memories,
            summary=conversation.summary,
        )

        if tool_defs is None:
            tool_defs = get_tool_schema()

        # 工具调用主循环（首次 chat → 无工具则流式 / 有工具则循环）整体在独立模块里
        async for event in run_tool_loop(
            self.llm_client, messages, tool_defs, settings.MAX_TOOL_ROUND
        ):
            yield event

    async def _apply_feedback(self, feedback: str, current_plan: dict, conversation):
        """根据用户反馈调整现有行程"""
        await self.update_summary(conversation)
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
            summary=conversation.summary,
        )

        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

    async def gossip(self, conversation):
        context = await conversation.get_context(
            max_tokens=settings.CONTEXT_WINDOW_MAX_TOKENS,
            token_counter=self.llm_client.count_tokens,
        )

        if not context:
            yield {
                "type": "token",
                "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？",
            }
            return

        await self.update_summary(conversation)

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref,
            memories=conversation.memories,
            summary=conversation.summary,
        )

        full_text = ""

        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
            yield {"type": "token", "content": chunk}

        await conversation.add_message("assistant", full_text)
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
