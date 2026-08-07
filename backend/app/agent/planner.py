"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""
from redis.asyncio import Redis

from backend.app.services.prompt_builder import PromptBuilder
from backend.app.services.llm_client import LLMClient
from backend.app.crud.trip import find_trip_by_id, update_trip
from backend.app.tools import get_tool_schema, execute_tool
import json
import re
from backend.app.config import settings
from backend.app.memory.preferences import load_preferences, extract_preferences, save_preferences

MAX_TOOL_ROUND = 10


class TripPlannerAgent:
    """行程规划 Agent 核心"""

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()

    async def handle_message(self, user_input: str, conversation, r: Redis):
        """Agent 主入口：接收用户消息，返回 Agent 回复（流式）"""
        conversation.pref = await load_preferences(r, conversation.user_id)

        # 1. 保存用户消息
        await conversation.add_message("user", user_input)

        # 2. 意图判断及分支选择
        intent = await self.llm_classify_intent(user_input, conversation)

        if intent == "new_trip":
            stream = self._generate_plan(conversation)
        elif intent == "modify_trip":
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
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
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

        # 5. 保存解析出的行程数据
        if plan_data is not None:
            try:
                await update_trip(conversation.db, conversation.trip_id, plan_data=plan_data)

            except Exception as e:
                print(f"[ERROR] 保存行程失败: {e}")

        # 6. 保存 AI 回复（自然语言部分，不含 JSON 代码块）
        await conversation.add_message("assistant", display_text)
        new_pref = extract_preferences(user_input)
        if new_pref:
            await save_preferences(r, conversation.user_id, new_pref)

        # 7. 结束 — 把 trip_id 带回前端，让前端知道"刚聊的是哪个行程"
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}

    def _extract_plan_json(self, full_text: str) -> tuple[str, dict | None]:
        """从 LLM 回复中分离自然语言文本与 ```json 代码块。

        返回 (display_text, plan_data)。display_text 是展示给用户的自然语言，
        plan_data 是解析后的行程 JSON；如果未找到 JSON 块，则 plan_data 为 None，
        display_text 为原始文本。
        """
        plan_data = None

        # 优先：按 ```json / ``` 标记拆分
        parts = full_text.split("```json", 1)
        if len(parts) == 2:
            display_text = parts[0].strip()
            json_part = parts[1]
            end = json_part.rfind("```")
            if end != -1:
                json_str = json_part[:end].strip()
            else:
                json_str = json_part.strip()

            if json_str:
                try:
                    plan_data = json.loads(json_str)
                except (json.JSONDecodeError, TypeError):
                    pass

            if plan_data is not None:
                return display_text, plan_data

        # 回退 1：尝试按普通的 ``` 标记提取 JSON
        triple_parts = full_text.split("```", 1)
        if len(triple_parts) == 2:
            # 第一个 ``` 之后、最后一个 ``` 之前的内容
            rem = triple_parts[1]
            end2 = rem.rfind("```")
            candidate = (rem[:end2] if end2 != -1 else rem).strip()
            # 去掉可能的前导 "json" 标记
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                plan_data = json.loads(candidate)
                display_text = full_text.split("```")[0].strip()
                return display_text, plan_data
            except (json.JSONDecodeError, TypeError):
                pass

        # 回退 2：兼容没有 ```json 标记的纯 JSON 输出
        match = re.search(r'\{.*}', full_text, re.DOTALL)
        if match:
            try:
                plan_data = json.loads(match.group())
                display_text = full_text.replace(match.group(), "").strip()
                return display_text, plan_data
            except (json.JSONDecodeError, TypeError):
                pass

        print(f"[WARN] 未在回复中找到有效 JSON，原始输出前200字: {full_text[:200]}")
        return full_text, None

    async def llm_classify_intent(self, user_input: str, conversation):
        """LLM轻量意图识别"""
        intent_classifier_prompt = self.prompt_builder.build_intent_classifier_prompt()

        # 构建 messages
        message = [{
            "role": "system",
            "content": intent_classifier_prompt
        }]

        # 检查对话历史
        context_hint = ""
        if conversation.trip_id != 0:
            context_hint = (
                f"当前对话有一个已存在的行程（ID={conversation.trip_id}），"
                f"状态为 {conversation.state.value}。"
                f"如果用户提到修改、调整、更换等，应归类为 modify_trip。"
            )

        # 将上下文历史加入 messages
        if context_hint != "":
            message.append({
                "role": "system",
                "content": context_hint
            })
        message.append({
            "role": "user",
            "content": user_input
        })

        try:
            resp = await self.llm_client.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=message,
                stream=False,
                timeout=settings.LLM_REQUEST_TIMEOUT,
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(resp.choices[0].message.content)
            intent = result.get("intent", "unclear")
            if intent not in ("new_trip", "modify_trip", "ask_question", "unclear"):
                intent = "unclear"
            return intent
        except Exception as e:
            print(f"[WARN] LLM 意图分类失败，回退关键词: {e}")
            # 4. fallback 到关键词匹配
            return self._keyword_classify(user_input)

    def _keyword_classify(self, user_input: str):
        """老方法：关键词匹配"""
        text = user_input.strip()

        # 修改意图的关键词
        modified_keywords = ["修改", "调整", "换", "去掉", "增加", "改成", "不要", "换个"]
        if any(kw in text for kw in modified_keywords):
            return "modify_trip"

        # 新行程的关键词
        new_keywords = ["规划", "想去", "安排", "帮我", "推荐", "三日", "几日", "旅游", "旅行"]
        if any(kw in text for kw in new_keywords):
            return "new_trip"

        # 提问类
        question_keywords = ["?", "？", "怎么样", "如何", "什么是", "介绍一下"]
        if any(kw in text for kw in question_keywords):
            return "ask_question"

        return "unclear"

    async def _generate_plan(self, conversation, tool_defs=None):
        """构造 Prompt 调用 LLM 生成行程"""
        context = await conversation.get_context(max_tokens=30000, token_counter=self.llm_client.count_tokens)

        if not context:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref
        )

        if tool_defs is None:
            tool_defs = get_tool_schema()

        thoughts : list[str] = []

        # 非流式调用LLM
        message = await self.llm_client.chat(messages, tool_defs)
        if not message.tool_calls:
            # 没有工具调用的需求，则yield流式输出
            async for chunk in self.llm_client.chat_stream(messages):
                yield {"type": "token", "content": chunk}
            return
        tool_round = 0
        while tool_round < MAX_TOOL_ROUND:
            tool_round += 1

            messages.append({
                "role": "assistant",
                "content": message.content,  # 可能为 None
                "tool_calls": message.tool_calls  # tool_calls 列表
            })



            tool_names = ", ".join(tool_call.function.name for tool_call in message.tool_calls)

            yield {"type": "thinking", "content": f"我现在要使用 {tool_names} 工具以确认安排"}

            observations = []

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                result = await execute_tool(fn_name, **fn_args)

                observations.append(f"{fn_name}({fn_args}) → {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # 在 observations 循环结束、调用下一轮 LLM 之前
            summary = "; ".join(obs[:120] for obs in observations)
            thoughts.append(f"第{tool_round}轮：调用了 {tool_names}，结果：{summary[:150]}")

            messages.append({
                "role": "assistant",
                "content": (
                        "[内部推理] 我目前已掌握的信息：\n"
                        + "\n".join(f"- {t}" for t in thoughts[-3:])
                        + "\n\n请基于以上信息评估：是否已满足用户需求？"
                          "若已满足，直接组织最终行程回答，不要调用工具；"
                          "若关键信息仍有缺失，再调用工具补充。"
                ),
            })

            message = await self.llm_client.chat(messages, tool_defs)

            if not message.tool_calls:
                async for chunk in self.llm_client.chat_stream(messages):
                    yield {"type": "token", "content": chunk}
                return

        # 调用上限后的兜底处理
        # ← 走到这里说明 10 轮工具调用后 LLM 还在要工具
        print(f"[WARN] 工具调用超过 {MAX_TOOL_ROUND} 轮，强制结束")
        # 兜底：把当前上下文流式输出
        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

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
        context = await conversation.get_context(max_tokens=30000, token_counter=self.llm_client.count_tokens)

        if not context:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref
        )

        full_text = ""

        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
            yield {"type": "token", "content": chunk}

        await conversation.add_message("assistant", full_text)
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
