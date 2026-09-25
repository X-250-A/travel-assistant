"""
PromptBuilder: System Prompt 模板 + 上下文拼接
"""

from pathlib import Path


class PromptBuilder:
    """System Prompt + 上下文组装"""

    def __init__(self):
        system_prompt_path = Path(__file__).parent / "prompts" / "trip-agent-system-prompt.txt"
        intent_classifier_prompt_path = (
            Path(__file__).parent / "prompts" / "intent-classifier-prompt.txt"
        )
        critic_prompt_path = Path(__file__).parent / "prompts" / "critic-prompt.txt"
        memory_extract_prompt_path = Path(__file__).parent / "prompts" / "memory-extract-prompt.txt"
        query_rewrite_prompt_path = Path(__file__).parent / "prompts" / "query-rewrite-prompt.txt"
        pref_extract_prompt_path = Path(__file__).parent / "prompts" / "pref-extract-prompt.txt"
        summary_prompt_path = Path(__file__).parent / "prompts" / "summary-prompt.txt"

        self.system_prompt = system_prompt_path.read_text("utf-8")
        self.intent_classifier_prompt = intent_classifier_prompt_path.read_text("utf-8")
        self.critic_prompt = critic_prompt_path.read_text("utf-8")
        self.memory_extract_prompt = memory_extract_prompt_path.read_text("utf-8")
        self.query_rewrite_prompt = query_rewrite_prompt_path.read_text("utf-8")
        self.pref_extract_prompt = pref_extract_prompt_path.read_text("utf-8")
        self.summary_prompt = summary_prompt_path.read_text("utf-8")

    def render_preferences(self, pref: dict[str, str] | None) -> str:
        if not pref:
            return ""
        lines = []
        for key, value in pref.items():
            item = value.split(",")
            lines.append(f"- {key}: {'、'.join(item)}")
        return "用户偏好（必须严格遵守，违反即为错误）：\n" + "\n".join(lines)

    def render_vector_memory(self, memories: list[str] | None) -> str:
        if not memories:
            return ""
        line = [f" - {m}" for m in memories]
        return "【历史相关记忆（跨会话，参考但可覆盖）】\n" + "\n".join(line)

    def render_summary_prompt(self, summary: str) -> str:
        if not summary:
            return ""
        return "【对话脉络摘要】\n" + summary

    def build_system_prompt(self) -> str:
        """返回 System Prompt（静态模板）"""
        return self.system_prompt

    def build_intent_classifier_prompt(self) -> str:
        """返回 Intent_classifier Prompt（静态模板）"""
        return self.intent_classifier_prompt

    def build_critic_prompt(self) -> str:
        """返回 critic Prompt（静态模板）"""
        return self.critic_prompt

    def build_memory_extract_prompt(self, user_input: str) -> str:
        # 用 replace 而非 format：prompt 里的 JSON 示例含 {should_save}/{facts}，
        # .format() 会把这些字面花括号当占位符，抛 KeyError: 'should_save'
        return self.memory_extract_prompt.replace("{user_input}", user_input)

    def build_query_rewrite_prompt(self, user_input: str, history_text: str) -> str:
        # 同上：replace 而非 format，避免 JSON 示例里的花括号被当占位符
        return self.query_rewrite_prompt.replace("{user_input}", user_input).replace(
            "{history}", history_text
        )

    def build_pref_extract_prompt(self, user_input: str) -> str:
        return self.pref_extract_prompt.replace("{user_input}", user_input)

    def build_summary_prompt(self, old_summary: str, evicted_messages: str) -> str:
        return self.summary_prompt.replace("{old_summary}", old_summary or "").replace(
            "{evicted_messages}", evicted_messages
        )

    def build_messages(
        self,
        history: list[dict],
        user_input: str,
        pref: dict[str, str] | None = None,
        extra_system: str | None = None,
        memories: list[str] | None = None,
        summary: str | None = None,
    ) -> list[dict]:
        """拼接 messages 数组"""
        preferences = self.render_preferences(pref)
        vector_memory = self.render_vector_memory(memories)
        system_msgs = [{"role": "system", "content": self.system_prompt}]
        if extra_system:
            system_msgs.append({"role": "system", "content": extra_system})
        if preferences:
            system_msgs.append({"role": "system", "content": preferences})
        if vector_memory:
            system_msgs.append({"role": "system", "content": vector_memory})
        if summary:
            processed_summary = self.render_summary_prompt(summary)
            system_msgs.append({"role": "system", "content": processed_summary})
        return [*system_msgs, *history, {"role": "user", "content": user_input}]
