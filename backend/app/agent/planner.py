"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""
from backend.app.services.prompt_builder import PromptBuilder
from backend.app.services.llm_client import LLMClient
from backend.app.crud.trip import find_trip_by_id, update_trip
import json
import re
from backend.app.tools.weather import WEATHER_TOOL, get_weather


TOOL_MAP = {
    "get_weather": get_weather
}





class TripPlannerAgent:
    """行程规划 Agent 核心"""
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()

    async def handle_message(self, user_input: str, conversation):
        """Agent 主入口：接收用户消息，返回 Agent 回复（流式）"""
        # 1. 保存用户消息
        await conversation.add_message("user", user_input)

        # 2. 意图判断及分支选择
        intent = self._classify_intent(user_input)

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
            stream = self._generate_plan(conversation)
        else:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            yield {"type": "done", "data": {}}
            return

        # 3. 消费流式生成器，一边 yield token，一边收集完整文本
        full_text = ""
        async for chunk in stream:
            full_text += chunk
            yield {"type": "token", "content": chunk}

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

        # 7. 结束 — 把 trip_id 带回前端，让前端知道"刚聊的是哪个行程"
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}

    def _extract_plan_json(self, full_text: str) -> tuple[str, dict | None]:
        """从 LLM 回复中分离自然语言文本与 ```json 代码块。

        返回 (display_text, plan_data)。display_text 是展示给用户的自然语言，
        plan_data 是解析后的行程 JSON；如果未找到 JSON 块，则 plan_data 为 None，
        display_text 为原始文本。
        """
        plan_data = None
        display_text = full_text

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

    def _classify_intent(self, user_input: str):
        """分类用户意图：new_trip / modify_trip / ask_question / unclear"""
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

    async def _generate_plan(self, conversation, tool_defs = None):
        """构造 Prompt 调用 LLM 生成行程"""
        context = await conversation.get_context(max_tokens=30000)

        if not context:
            yield "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
        )

        if tool_defs is None:
            tool_defs = [WEATHER_TOOL]

        # 非流式调用LLM
        message = await self.llm_client.chat(messages, tool_defs)
        if not message.tool_calls:
            # 没有工具调用的需求，则yield流式输出
            async for chunk in self.llm_client.chat_stream(messages):
                yield chunk
            return

        while True:

            messages.append({
                "role": "assistant",
                "content": message.content,  # 可能为 None
                "tool_calls": message.tool_calls  # tool_calls 列表
            })


            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                fn = TOOL_MAP.get(fn_name)
                if fn is None:
                    result = f"未知工具：{fn_name}"
                else:
                    result = await fn(**fn_args)
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id" : tool_call.id,
                    "content" : result,
                })

            message = await self.llm_client.chat(messages, tool_defs)

            if not message.tool_calls:
                async for chunk in self.llm_client.chat_stream(messages):
                    yield chunk
                return











    async def _apply_feedback(self, feedback: str, current_plan: dict, conversation):
        """根据用户反馈调整现有行程"""
        modify_prompt = f"""以下是当前行程的完整 JSON：
{json.dumps(current_plan, ensure_ascii=False, indent=2)}

用户要求：{feedback}

请在现有行程基础上做局部调整。只修改用户提到的部分，其余保持不变。
先用自然语言说明你做了哪些调整，然后在回复末尾用 ```json 代码块返回修改后的完整行程 JSON。"""
        # 保留原始 system prompt 的角色定义，再追加修改指令
        messages = [
            {"role": "system", "content": self.prompt_builder.system_prompt},
            {"role": "system", "content": modify_prompt},
            *conversation.history_cache,
        ]

        async for chunk in self.llm_client.chat_stream(messages):
            yield chunk
