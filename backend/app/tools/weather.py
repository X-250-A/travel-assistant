import random
import datetime
import httpx
from backend.app.db.redis import get_redis
from backend.app.config import settings
from backend.app.tools.base import Tool


WEATHER_PARAMETERS = {
    "city": {
        "type": "string",
        "description": "城市名称，如北京，上海等"
    },
    "date": {
        "type": "string",
        "description": "日期，格式为 YYYY-MM-DD，不传则查当天"
    }
}



async def get_weather(city : str, date : str = None):
    api_key = settings.WEATHER_API_KEY

    # key归一化，预防同一数据不同写法导致key不同，降低缓存命中率
    normalized_date = date or datetime.date.today().isoformat()

    # 查缓存，命中则返回
    cache_key = f"weather:{city}:{normalized_date}"
    r = await get_redis(0)
    cached = await r.get(cache_key)
    await r.aclose()
    if cached:
        return cached

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


    r = await get_redis(0)
    await r.setex(cache_key, settings.WEATHER_CACHE_TTL + random.randint(-300, 300), result)
    await r.aclose()

    return result

weather_tool = Tool(
    name = "get_weather",
    description="查询目的地指定日期的天气预报，用于在行程规划中给出天气提醒和出行建议",
    parameters=WEATHER_PARAMETERS,
    required=["city"],
    handler=get_weather
)