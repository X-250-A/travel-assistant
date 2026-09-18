import contextlib
import json
import logging
import re

logger = logging.getLogger(__name__)


class PlanJSONExtractor:
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
            json_str = json_part[:end].strip() if end != -1 else json_part.strip()

            if json_str:
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    plan_data = json.loads(json_str)

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
            except json.JSONDecodeError, TypeError:
                pass

        # 回退 2：兼容没有 ```json 标记的纯 JSON 输出
        match = re.search(r"\{.*}", full_text, re.DOTALL)
        if match:
            try:
                plan_data = json.loads(match.group())
                display_text = full_text.replace(match.group(), "").strip()
                return display_text, plan_data
            except json.JSONDecodeError, TypeError:
                pass

        logger.warning("未在回复中找到有效 JSON，原始输出前200字：%s", full_text[:200])
        return full_text, None
