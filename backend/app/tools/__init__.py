"""tools 注册中心 — 统一导出工具定义、底层函数与执行入口"""

from backend.app.tools.base import Tool
from backend.app.tools.budget_calculate import budget_calculate, budget_calculate_tool
from backend.app.tools.poi import format_pois, poi_tool, search_poi
from backend.app.tools.transport_guiding import transport_guiding, transport_guiding_tool
from backend.app.tools.weather import get_weather, weather_tool

ALL_TOOLS: list = [
    weather_tool,
    budget_calculate_tool,
    transport_guiding_tool,
    poi_tool,
]


def get_tool_schema():
    return [tool.openai_schema() for tool in ALL_TOOLS]


async def execute_tool(name: str, **kwargs):
    for tool in ALL_TOOLS:
        if tool.name == name:
            if tool.handler is None:
                return f"工具 {name} 没有实现函数"
            return await tool.handler(**kwargs)
    return f"未知工具 {name}"


__all__ = [
    "Tool",
    "ALL_TOOLS",
    "get_tool_schema",
    "execute_tool",
    "weather_tool",
    "budget_calculate_tool",
    "transport_guiding_tool",
    "poi_tool",
    "get_weather",
    "budget_calculate",
    "transport_guiding",
    "format_pois",
    "search_poi",
]
