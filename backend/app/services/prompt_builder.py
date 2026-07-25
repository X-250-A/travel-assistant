"""
PromptBuilder: System Prompt 模板 + 上下文拼接
"""
from pathlib import Path


class PromptBuilder:
    """System Prompt + 上下文组装"""
    def __init__(self):
        prompt_path = Path(__file__).parent / "prompts" / "trip-agent-system-prompt.txt"
        self.system_prompt = prompt_path.read_text("utf-8")

    def build_system_prompt(self) -> str:
        """返回 System Prompt（静态模板）"""
        return self.system_prompt


    def build_messages(self, history : list[dict], user_input: str) -> list[dict]:
        """拼接 messages 数组"""
        return [
            {"role" : "system", "content" : self.system_prompt},
            *history,
            {"role" : "user", "content" : user_input}
        ]
