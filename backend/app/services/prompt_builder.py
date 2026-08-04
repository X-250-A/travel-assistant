"""
PromptBuilder: System Prompt 模板 + 上下文拼接
"""
from pathlib import Path



class PromptBuilder:
    """System Prompt + 上下文组装"""
    def __init__(self):
        system_prompt_path = Path(__file__).parent / "prompts" / "trip-agent-system-prompt.txt"
        intent_classifier_prompt_path = Path(__file__).parent / "prompts" / "intent-classifier-prompt.txt"
        self.system_prompt = system_prompt_path.read_text("utf-8")
        self.intent_classifier_prompt = intent_classifier_prompt_path.read_text("utf-8")

    def render_preferences(self, pref: dict[str, str] | None) -> str:
        lines = []
        if not pref:
            return ""
        for key, value in pref.items():
            item = value.split(",")
            lines.append(f"- {key}: {"、".join(item)}")
        return "用户偏好（必须严格遵守，违反即为错误）：\n" + "\n".join(lines)

    def build_system_prompt(self) -> str:
        """返回 System Prompt（静态模板）"""
        return self.system_prompt

    def build_intent_classifier_prompt(self) -> str:
        """返回 Intent_classifier Prompt（静态模板）"""
        return self.intent_classifier_prompt


    def build_messages(self, history : list[dict], user_input: str, pref : dict[str, str] | None = None, extra_system: str | None = None) -> list[dict]:
        """拼接 messages 数组"""
        preferences = self.render_preferences(pref)
        system_msgs = [{"role" : "system", "content" : self.system_prompt}]
        if extra_system:
            system_msgs.append({"role" : "system", "content" : extra_system})
        if preferences:
            system_msgs.append({"role" : "system", "content" : preferences})
        return [
                *system_msgs,
                *history,
                {"role" : "user", "content" : user_input}
        ]
