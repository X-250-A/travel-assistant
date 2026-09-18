"""PlanData 校验模型 —— LLM 输出的行程 JSON 必须通过这里的结构校验才算合法方案。

字段清单来源（两份事实，已对齐）：
- services/prompts/trip-agent-system-prompt.txt 第 37-72 行定义的 JSON 结构
- frontend/types/index.ts 的 PlanData / DayPlan / Attraction / Meal 接口

设计原则：拦「结构错误」（必填字段缺失 / 类型错 / 嵌套坏），容「内容不完整」
（展示性字段给默认值）。原因：LLM 输出不稳定，一个展示字段漏了就把整份方案
作废，代价远大于收益；但结构字段（destination/duration/days）缺失则前端
无法渲染，必须拦住。
"""

from pydantic import BaseModel, Field


class Attraction(BaseModel):
    name: str
    type: str = "景点"
    duration_minutes: int = 0
    cost_yuan: int = 0
    tips: str = ""
    transport_from_previous: str | None = None


class Meal(BaseModel):
    meal_type: str
    suggestion: str = ""
    location_near: str = ""


class DayPlan(BaseModel):
    day: int = Field(..., ge=1)
    date: str | None = None
    theme: str = ""
    attractions: list[Attraction] = []
    meals: list[Meal] = []


class PlanData(BaseModel):
    destination: str
    duration: int = Field(..., ge=1)
    budget: float = 0
    style: list[str] = []
    overview: str = ""
    days: list[DayPlan]
    overall_tips: str = ""
