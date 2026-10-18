import logging

from pydantic import ValidationError

from backend.app import settings
from backend.app.agent.conversation import ConversationState
from backend.app.schemas.intent import Intent, IntentResult

logger = logging.getLogger(__name__)

# 状态 → 决策参考文案。键引用 ConversationState 枚举（单一真源）：
# 新增状态必须在此补档，禁止手写状态名字符串（与枚举漂移 = 霰弹式修改）。
_STATE_GUIDE: dict[ConversationState, str] = {
    ConversationState.IDLE: "IDLE（无方案）: 当前没有已生成方案，用户不可能确认方案，confirm 意图无效\n",
    ConversationState.CONFIRMING: "CONFIRMING（有方案未确认）: 用户说可以/行/就这么定，应归为 confirm；说修改才归 modify_trip\n",
    ConversationState.DONE: "DONE（已确认）: 行程已确认，若用户提修改，修改后需重新确认\n",
}


class IntentClassifier:
    async def llm_classify_intent(self, user_input: str, conversation) -> Intent:
        """LLM轻量意图识别"""
        intent_classifier_prompt = self.prompt_builder.build_intent_classifier_prompt()

        # 构建 messages
        message = [{"role": "system", "content": intent_classifier_prompt}]

        # 检查对话历史
        context_hint = ""
        if conversation.trip_id != 0:
            context_hint = (
                f"当前对话有一个已存在的行程（ID={conversation.trip_id}），"
                f"状态为 {conversation.state.value}。"
                f"请你根据当前会话状态以及以下对应状态决策参考，进行对应决策\n"
                f"{_STATE_GUIDE[ConversationState.IDLE]}"
                f"{_STATE_GUIDE[ConversationState.CONFIRMING]}"
                f"{_STATE_GUIDE[ConversationState.DONE]}"
            )

        # 将上下文历史加入 messages
        if context_hint != "":
            context = await conversation.get_context(
                max_tokens=2000,
                token_counter=self.llm_client.count_tokens,
            )
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in context[:-1])
            message.append({"role": "system", "content": history_text})
            message.append({"role": "system", "content": context_hint})
        message.append({"role": "user", "content": user_input})

        try:
            resp = await self.llm_client.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=message,
                stream=False,
                timeout=settings.LLM_REQUEST_TIMEOUT,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return IntentResult.model_validate_json(resp.choices[0].message.content).intent
        except ValidationError as e:
            logger.warning("意图值非法，归为 unclear：%s", e)
            return Intent.UNCLEAR
        except Exception as e:
            logger.warning("LLM 意图分类失败，回退关键词：%s", e)
            # 4. fallback 到关键词匹配
            return self._keyword_classify(user_input)

    def _keyword_classify(self, user_input: str) -> Intent:
        """老方法：关键词匹配"""
        text = user_input.strip()

        # 修改意图的关键词
        modified_keywords = ["修改", "调整", "换", "去掉", "增加", "改成", "不要", "换个"]
        if any(kw in text for kw in modified_keywords):
            return Intent.MODIFY_TRIP

        # 新行程的关键词
        new_keywords = ["规划", "想去", "安排", "帮我", "推荐", "三日", "几日", "旅游", "旅行"]
        if any(kw in text for kw in new_keywords):
            return Intent.NEW_TRIP

        # 提问类
        question_keywords = ["?", "？", "怎么样", "如何", "什么是", "介绍一下"]
        if any(kw in text for kw in question_keywords):
            return Intent.ASK_QUESTION

        return Intent.UNCLEAR
