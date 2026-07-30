from backend.app.tools.weather import weather_tool
from backend.app.tools.budget_calculate import budget_calculate_tool
from backend.app.tools.transport_guiding import transport_guiding_tool
from backend.app.tools.base import Tool

ALL_TOOLS : list = [
    weather_tool,
    budget_calculate_tool,
    transport_guiding_tool,
]

def get_tool_schema():
    return [tool.openai_schema() for tool in ALL_TOOLS]


async def execute_tool(name : str,**kwargs):
    for tool in ALL_TOOLS:
        if tool.name == name:
            if tool.handler is None:
                return f"工具 {name} 没有实现函数"
            return await tool.handler(**kwargs)
    return f"未知工具 {name}"
