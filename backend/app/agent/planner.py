"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""
from backend.app.services.prompt_builder import PromptBuilder
from backend.app.services.llm_client import LLMClient
from backend.app.crud.trip import find_trip_by_id, update_trip
import json
import re


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

        # 4. 尝试解析 JSON 并保存行程
        try:
            plan_data = json.loads(full_text)
            await update_trip(conversation.db, conversation.trip_id, plan_data=plan_data)
        except (json.JSONDecodeError, TypeError):
            # LLM 可能在 JSON 前后加了文字，尝试用正则提取
            match = re.search(r'\{.*}', full_text, re.DOTALL)
            if match:
                try:
                    plan_data = json.loads(match.group())
                    await update_trip(conversation.db, conversation.trip_id, plan_data=plan_data)
                except Exception:
                    print(f"[WARN] JSON 解析失败，原始输出前200字: {full_text[:200]}")
            else:
                print(f"[WARN] 未在回复中找到 JSON，原始输出前200字: {full_text[:200]}")
        except Exception as e:
            print(f"[ERROR] 保存行程失败: {e}")

        # 5. 保存 AI 回复
        await conversation.add_message("assistant", full_text)

        # 6. 结束 — 把 trip_id 带回前端，让前端知道"刚聊的是哪个行程"
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}

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

    async def _generate_plan(self, conversation):
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

        async for chunk in self.llm_client.chat_stream(messages):
            yield chunk

    async def _apply_feedback(self, feedback: str, current_plan: dict, conversation):
        """根据用户反馈调整现有行程"""
        modify_prompt = f"""以下是当前行程的完整 JSON：
{json.dumps(current_plan, ensure_ascii=False, indent=2)}

用户要求：{feedback}

请在现有行程基础上做局部调整。只修改用户提到的部分，其余保持不变。
直接返回修改后的完整行程 JSON。"""
        # 保留原始 system prompt 的角色定义，再追加修改指令
        messages = [
            {"role": "system", "content": self.prompt_builder.system_prompt},
            {"role": "system", "content": modify_prompt},
            *conversation.history_cache,
        ]

        async for chunk in self.llm_client.chat_stream(messages):
            yield chunk
