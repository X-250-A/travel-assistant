from typing import Any
from dataclasses import dataclass, field
from collections.abc import Callable, Awaitable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str] = field(default_factory=list)
    handler: Callable[..., Awaitable[str]] | None = None

    def openai_schema(self) -> dict:
        """生成 OpenAI function-calling 格式的 tool 定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }
