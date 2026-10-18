"""LLM 纯 JSON 调用的结构化输出模型 —— 校验收口的单一真源。

每个模型对应一处 response_format=json_object 的调用，字段与该调用 prompt 的
JSON 契约一一对应。调用方统一用 model_validate_json 收口，避免手写
json.loads + dict 取值导致的 KeyError / 类型漂移。
"""

from enum import StrEnum

from pydantic import BaseModel


class QueryRewriteResult(BaseModel):
    """记忆检索 query 改写结果（query-rewrite-prompt）。"""

    need_rewrite: bool
    rewritten_query: str


class PrefType(StrEnum):
    """偏好类型清单 —— 只此一处定义，与 pref-extract-prompt、MERGE_RULES 对齐。"""

    DIET = "饮食"
    BUDGET = "预算"
    MOBILITY = "出行"
    PACE = "节奏"


class PrefItem(BaseModel):
    type: PrefType
    value: str


class PrefExtractResult(BaseModel):
    """用户偏好提取结果（pref-extract-prompt）。"""

    should_save: bool
    prefs: list[PrefItem] = []


class CriticResult(BaseModel):
    """行程质量审查结果（critic-prompt）。

    scores 三个维度键固定为 budget/preferences/feasibility，缺省时留空由调用方
    按"无分数即跳过分数校验"处理。
    """

    passed: bool
    scores: dict[str, int] = {}
    issues: list[str] = []


class MemoryExtractResult(BaseModel):
    """跨会话记忆提取结果（memory-extract-prompt）。"""

    should_save: bool
    facts: list[str] = []
