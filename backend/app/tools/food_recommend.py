import random

import httpx

from backend.app import settings
from backend.app.config import PLACEHOLDER_MARKER
from backend.app.db import get_redis
from backend.app.logging_config import logger
from backend.app.tools import Tool
from backend.app.tools.poi import format_pois

FOOD_PARAMETERS = {
    "city": {"type": "string", "description": "城市名称，如成都、杭州"},
    "keyword": {"type": "string", "description": "美食关键词，默认'美食'"},
    "limit": {"type": "integer", "description": "返回条数，默认10"},
}


async def food_recommend(city: str, keyword: str = "美食", limit: int = 10):
    """查询城市美食推荐（名称、类型、评分、价格、地址）。

    与 search_poi(景点) 区分：本工具聚焦餐饮/美食场景。
    """
    amap_api_key = settings.AMAP_API_KEY

    # 1. 降级：AMAP_API_KEY 仍是占位符 → 返回提示
    if PLACEHOLDER_MARKER in amap_api_key:
        return "暂未配置美食查询服务"

    # 2. Redis 读穿：key = food:{city}:{keyword}（避开 poi: 前缀，防与景点缓存互相污染）
    cache_key = f"food:{city}:{keyword}"
    try:
        r = await get_redis(0)
        cached = await r.get(cache_key)
        await r.aclose()
        if cached:
            return cached
    except Exception as e:
        logger.warning("美食缓存读取失败，跳过缓存：%s", e)

    # 3. miss → httpx 调高德 v3 place/text
    params = {
        "key": amap_api_key,
        "keywords": keyword,
        "city": city,
        "citylimit": "true",
        "offset": 20,
        "extensions": "all",
        "lang": "zh",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://restapi.amap.com/v3/place/text",
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.warning("美食查询失败(HTTP)：%s", e)
        return "美食推荐查询暂时不可用，请稍后再试"
    except Exception as e:
        logger.error("美食查询异常：%s", e)
        return "美食推荐查询暂时不可用，请稍后再试"

    # 防线：高德业务失败(status != 1) → 把错误信息透传给 LLM
    if data.get("status") != "1":
        return f"美食查询失败：{data.get('info', '未知错误')}"

    # 4. 格式化返回字符串
    pois = data.get("pois", [])
    results = format_pois(pois, city, limit)

    # 5. 写缓存 + 预防缓存雪崩
    try:
        r = await get_redis(0)
        await r.setex(cache_key, settings.POI_CACHE_TTL + random.randint(-600, 600), results)
        await r.aclose()
    except Exception as e:
        logger.warning("美食缓存写入失败：%s", e)

    return results


food_recommend_tool = Tool(
    name="food_recommend",
    description=(
        "查询指定城市的美食/餐饮推荐（店名、类型、评分、人均价格、地址），用于行程规划时向用户推荐合适的餐厅；"
        "注意区别于 search_poi(景点推荐)"
    ),
    parameters=FOOD_PARAMETERS,
    required=["city"],
    handler=food_recommend,
)
