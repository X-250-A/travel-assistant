"""意图分类的结构化输出模型 —— 校验收口的单一真源。

Intent 枚举 + IntentResult 模型：意图清单只在此处定义一次，
prompt 的可取值、LLM 输出的校验、planner 的分发都从 Intent 派生，
避免「清单散落在 prompt / 白名单 / if-elif 三处」的漂移。
"""

from enum import StrEnum

from pydantic import BaseModel


class Intent(StrEnum):
    NEW_TRIP = "new_trip"
    MODIFY_TRIP = "modify_trip"
    ASK_QUESTION = "ask_question"
    CONFIRM = "confirm"
    UNCLEAR = "unclear"


class IntentResult(BaseModel):
    intent: Intent
