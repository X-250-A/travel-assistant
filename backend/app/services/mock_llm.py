"""
Mock LLM：LLM_PROVIDER=mock 时启用（E2E 测试专用）。

设计原则：E2E 只 mock 不可控的 LLM 回复，其余链路（前端渲染、SSE 流式、
后端路由、数据库落库、Redis）全部真实。

按 system prompt 特征路由到不同调用点，返回预设响应：
  - 意图分类（intent-classifier-prompt） → {"intent": "new_trip"}
  - 记忆提取（memory-extract-prompt）   → {"should_save": false, "facts": []}
  - Critic 审查（critic-prompt）        → {"passed": true, "issues": []}
  - 行程生成（chat 非流式）             → 无工具调用，直接进入流式输出
  - 行程生成（chat_stream 流式）        → 固定行程 Markdown（含 ```json 块）
"""

import json
from types import SimpleNamespace

# ── 行程模板（必须能被 planner._extract_plan_json 的 ```json 解析） ──────
# 字段对齐 frontend/components/trip/TripDetail.tsx：
#   destination / duration / budget / style / overview /
#   days[].{day, theme, attractions[], meals[]} / overall_tips
_PLAN_JSON = {
    "title": "成都 3 日游",
    "destination": "成都",
    "duration": 3,
    "budget": 3000,
    "style": ["美食", "文化"],
    "overview": "深度体验成都的市井烟火与历史文化。",
    "days": [
        {
            "day": 1,
            "theme": "市区经典",
            "attractions": [
                {
                    "name": "武侯祠",
                    "type": "博物馆",
                    "duration_minutes": 120,
                    "cost_yuan": 50,
                    "transport_from_previous": "步行",
                    "tips": "避开周末人流高峰",
                },
                {
                    "name": "锦里",
                    "type": "街区",
                    "duration_minutes": 90,
                    "cost_yuan": 0,
                    "transport_from_previous": "步行",
                    "tips": "",
                },
                {
                    "name": "宽窄巷子",
                    "type": "街区",
                    "duration_minutes": 90,
                    "cost_yuan": 0,
                    "transport_from_previous": "地铁",
                    "tips": "",
                },
            ],
            "meals": [
                {"meal_type": "breakfast", "suggestion": "担担面", "location_near": "武侯祠"},
                {"meal_type": "lunch", "suggestion": "火锅", "location_near": "锦里"},
                {"meal_type": "dinner", "suggestion": "川菜", "location_near": "宽窄巷子"},
            ],
        },
        {
            "day": 2,
            "theme": "熊猫与文创",
            "attractions": [
                {
                    "name": "成都大熊猫繁育研究基地",
                    "type": "动物园",
                    "duration_minutes": 180,
                    "cost_yuan": 55,
                    "transport_from_previous": "打车",
                    "tips": "早上 7 点前到能看到熊猫吃竹子",
                }
            ],
            "meals": [],
        },
    ],
    "overall_tips": "成都地铁方便，建议办一张天府通卡。",
}

TRIP_MARKDOWN = (
    "好的，已为您规划好成都 3 日游方案！\n\n"
    "## 第一天：市区经典\n\n"
    "- 武侯祠 → 锦里 → 宽窄巷子\n\n"
    "```json\n"
    + json.dumps(_PLAN_JSON, ensure_ascii=False, indent=2)
    + "\n```"
)


def _route(messages: list[dict]) -> str:
    """根据 system prompt 特征判断本次调用用途（特征词来自各 prompt 模板首句）"""
    text = " ".join(str(m.get("content", "")) for m in messages)
    if "意图分类器" in text:
        return "intent"
    if "行程质量审查员" in text:
        return "critic"
    if "记忆提取器" in text:
        return "memory"
    return "plan"


def mock_chat(messages: list[dict], tools: list[dict] | None):
    """非流式调用：返回带 .content / .tool_calls 的轻量对象，对齐 OpenAI message"""
    route = _route(messages)
    if route == "intent":
        content = '{"intent": "new_trip", "reason": "mock: E2E 固定返回新行程"}'
    elif route == "memory":
        content = '{"should_save": false, "facts": []}'
    elif route == "critic":
        content = (
            '{"passed": true,'
            ' "scores": {"budget": 90, "preferences": 95, "feasibility": 92},'
            ' "issues": []}'
        )
    else:
        # 行程生成首轮：不调用工具，直接进入 chat_stream 流式输出
        return SimpleNamespace(content=None, tool_calls=None)
    return SimpleNamespace(content=content, tool_calls=None)


async def mock_chat_stream(messages: list[dict]):
    """流式调用：分两次 yield 模拟"开始→结束"效果。

    不用 split(" ") 是因为前端用 `+=` 拼接 chunk，会丢失所有空格（导致"成都3日"变"成都3日"）。
    """
    yield TRIP_MARKDOWN[: len(TRIP_MARKDOWN) // 2]
    yield TRIP_MARKDOWN[len(TRIP_MARKDOWN) // 2 :]


# ── 底层 SDK 兼容（意图分类 / Critic 直接调 client.chat.completions.create） ──


class _MockCompletions:
    async def create(self, **kwargs):
        content = mock_chat(kwargs.get("messages", []), tools=None).content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _MockChat:
    def __init__(self):
        self.completions = _MockCompletions()


class MockOpenAIClient:
    """模拟 AsyncOpenAI：提供 chat.completions.create（async）"""

    def __init__(self):
        self.chat = _MockChat()
