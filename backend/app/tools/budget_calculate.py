from backend.app.tools.base import Tool

BUDGET_PARAMETERS = {
    "days" : {
        "type" : "integer",
        "description" : "旅游天数"
    },
    "people" : {
        "type" : "integer",
        "description" : "旅游人数"
    },
    "level" : {
        "type" : "string",
        "description" : "预算档次：经济/舒适/豪华"
    }
}

async def budget_calculate(days, people, level : str = "经济"):

    per_day = {
        "经济" : 300,
        "舒适" : 600,
        "豪华" : 1200
    }
    daily = per_day.get(level, 600)
    total = daily * people * days

    hotel = {"经济": 150, "舒适": 300, "豪华": 800}[level] * days


    transport = 50 * days * people
    food = {"经济": 80, "舒适": 150, "豪华": 400}[level] * days * people

    return (
        f"【{days}天{people}人 · {level}档预算估算】\n"
        f"  住宿：约 ¥{hotel}\n"
        f"  餐饮：约 ¥{food}\n"
        f"  交通：约 ¥{transport}\n"
        f"  景点门票+其他：约 ¥{total - hotel - food - transport}\n"
        f"  ──────────────\n"
        f"  总计：约 ¥{total}（人均 ¥{total // people}）\n"
        f"  建议预留 20% 弹性空间，实际准备 ¥{int(total * 1.2)} 左右。"
    )


budget_calculate_tool = Tool(
    name = "budget_calculate",
    description="根据旅行天数、人数和消费档次估算旅行预算总额及各分项费用",
    parameters=BUDGET_PARAMETERS,
    required=["days", "people"],
    handler=budget_calculate
)