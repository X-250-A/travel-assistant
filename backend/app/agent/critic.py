"""CriticReviewer mixin：行程方案质量审查"""

import json
import logging

from backend.app import settings

logger = logging.getLogger(__name__)


class CriticReviewer:
    async def _ask_critic(self, plan_data_json: dict, user_input: str, conversation):
        """构造 Prompt 调用 LLM 开始审查 Json"""
        extra_system = self.prompt_builder.build_critic_prompt()

        """ 拼接 message """
        messages = [{"role": "system", "content": extra_system}]

        messages.append(
            {
                "role": "user",
                "content": (
                    f"用户需求：{user_input}\n"
                    f"{self.prompt_builder.render_preferences(conversation.pref)}\n"
                    f"请审查以下行程 JSON：\n"
                    f"{json.dumps(plan_data_json, ensure_ascii=False, indent=2)}"
                ),
            }
        )

        """非流式调用LLM + 解析审查结果"""
        # 整个审查调用都可能失败（网络错误 / 返回非 JSON / 字段缺失），
        # 必须 try 包住，失败返回 None → 上层判定树降级用原方案，不阻断主流程
        try:
            response = await self.llm_client.client.chat.completions.create(
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
            if not isinstance(issues, list):
                issues = []
            issues = [str(i) for i in issues][:3]
        except Exception as e:
            logger.warning("审查结果解析失败：%s", e)
            return None

        return {"passed": passed, "scores": scores, "issues": issues}
