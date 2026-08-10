import httpx, random
from backend.app.tools.base import Tool
from backend.app.config import settings
from backend.app.db.redis import get_redis

POI_PARAMETERS = {
    "city": {"type": "string", "description": "城市名称，如成都、杭州"},
    "keyword": {"type": "string", "description": "景点关键词，默认'景点'"},
    "limit": {"type": "integer", "description": "返回条数，默认10"}
}

def format_pois(pois : list[dict], city : str, limit : int):
    lines = [f"{city} · 景点top {min(limit, len(pois))}"]
    for i, poi in enumerate(pois[:limit], start=1):
        name = poi.get("name", "未知景点")
        poi_type = (poi.get("type") or "").split(";")[0] or "其他"
        biz = poi.get("biz_ext") or {}
        rating = biz.get("rating") or "暂无"
        cost = biz.get("cost") or "0"
        address = poi.get("address") or ""
        lines.append(
            f"{i}·{name} | {poi_type} | 评分{rating} | 费用{cost} | {address}"
        )
    return "\n".join(lines)




async def search_poi(city: str, keyword: str = "景点", limit: int = 10):
    amap_api_key = settings.AMAP_API_KEY

    # 1. 降级:AMAP_API_KEY 含 "change-me" → 返回提示
    if "change-me" in amap_api_key:
        return "暂未配置景点查询服务"


    # 2. Redis 读穿:key = poi:{city}:{keyword}
    cache_key = f"poi:{city}:{keyword}"
    try:

        r = await get_redis(0) # 启动Redis
        cached = await r.get(cache_key) # 查询缓存
        await r.aclose() # 关闭Redis
        if cached:
            return cached
    except Exception as e:
        print(f"[WARN] 读穿失败，跳过缓存：{e}")


    # 3. miss → httpx 调高德 v3 place/text
    params = {
        "key": amap_api_key,
        "keywords": keyword,  # 不是 q!
        "city": city,  # 限定城市
        "citylimit": "true",  # 必加,防全国范围搜索
        "offset": 20,  # 每页条数
        "extensions": "all",  # 拿 open_time 等扩展字段
        "lang": "zh",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
            "https://restapi.amap.com/v3/place/text",
                params=params,
                timeout = 60
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"高德API查询失败：{e}")
        return "景点查询暂时不可用，请稍后再试"


    # 防线 3:高德业务失败(status != 1) → 把错误信息透传给 LLM
    if data.get("status") != "1":
        return f"景点查询失败：{data.get('info', '未知错误')}"


    # 4. 格式化返回字符串
    pois = data.get("pois", [])
    results = format_pois(pois, city, limit)


    # 添加缓存 + 预防缓存雪崩
    try:
        r = await get_redis(0)
        await r.setex(cache_key, settings.POI_CACHE_TTL + random.randint(-600, 600), results)
        await r.aclose()
    except Exception as e:
        print(f"Redis 写入缓存失败：{e}")

    return results

poi_tool = Tool(
    name="search_poi",
    description="查询指定城市的景点信息（名称、类型、评分、门票价格、地址），用于行程规划时向用户推荐合适的景点",
    parameters=POI_PARAMETERS,
    required=["city"],
    handler=search_poi
)




