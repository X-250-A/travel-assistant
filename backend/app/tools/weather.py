import httpx
from backend.app.config import settings


WEATHER_TOOL = {
    "type" : "function",
    "function" : {
        "name" : "get_weather",
        "description" : "查询目的地指定日期的天气预报，用于在行程规划中给出天气提醒和出行建议，如高温预警、降雨提醒、穿衣建议等",
        "parameters" : {
            "type" : "object",
            "properties" : {
                "city" : {
                    "type" : "string",
                    "description" : "城市名称，如北京，上海等"
                },
                "date" : {
                    "type" : "string",
                    "description" : "日期，格式为 YYYY-MM-DD，不传则查当天"
                }
            },
            "required" : ["city"]
        }
    }
}


async def get_weather(city : str, date : str = None):
    api_key = settings.WEATHER_API_KEY

    params = {
        "key" : api_key,
        "q" : city,
        "days" : date and 3 or 1,
        "lang" : "zh"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weatherapi.com/v1/forecast.json",
            params = params,
            timeout = 10,
        )
        resp.raise_for_status()
        data = resp.json()

    c = data["current"]
    result = f"【{city} 当前天气】\n"
    result += f"  天气：{c['condition']['text']}\n"
    result += f"  温度：{c['temp_c']}°C（体感 {c['feelslike_c']}°C）\n"
    result += f"  湿度：{c['humidity']}%　风速：{c['wind_kph']}km/h"

    return result

