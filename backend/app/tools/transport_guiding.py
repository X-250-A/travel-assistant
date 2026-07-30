import httpx
from math import radians, sin, cos, sqrt, asin
from backend.app.config import settings
from backend.app.tools.base import Tool

# 热门旅游城市经纬度（高德坐标系 GCJ-02）
CITY_COORDS = {
    "北京": "116.407526,39.904030",
    "上海": "121.473701,31.230416",
    "广州": "113.264385,23.129163",
    "深圳": "114.057868,22.543099",
    "成都": "104.066541,30.572269",
    "杭州": "120.155070,30.274085",
    "西安": "108.940174,34.341568",
    "重庆": "106.551556,29.563009",
    "武汉": "114.305392,30.593099",
    "南京": "118.796877,32.060255",
    "长沙": "112.938814,28.228209",
    "昆明": "102.832891,24.880095",
    "三亚": "109.511909,18.252847",
    "厦门": "118.089425,24.479833",
    "青岛": "120.382639,36.067082",
    "桂林": "110.290194,25.273565",
    "拉萨": "91.117328,29.647251",
    "哈尔滨": "126.535797,45.802756",
    "乌鲁木齐": "87.616848,43.825592",
}

DISTANCE_RULES = [
    (0, 200, "高铁", "高铁约0.5-2小时，建议优先选择高铁或自驾"),
    (200, 500, "高铁", "高铁约1-3小时，性价比最高"),
    (500, 1000, "高铁/飞机", "高铁约2-5小时，飞机约1.5-2小时（不含机场往返）"),
    (1000, 2000, "飞机", "建议乘坐飞机，航程约2-4小时"),
    (2000, float("inf"), "飞机", "建议乘坐飞机，航程约4-6小时"),
]

PRICE_ESTIMATE = {
    "高铁": {"基价": 0.5, "单位": "元/km"},
    "飞机": {"基价": 600, "单位": "元/人"},
    "自驾": {"基价": 0.6, "单位": "元/km"},
}

TRANSPORT_PARAMETERS = {
    "from_city": {
        "type": "string",
        "description": "出发城市名称，如北京、上海",
    },
    "to_city": {
        "type": "string",
        "description": "目的城市名称，如成都、杭州",
    },
    "preference": {
        "type": "string",
        "description": "出行偏好：速度优先 / 经济优先 / 均衡（默认均衡）",
    },
}


async def transport_guiding(from_city: str, to_city: str, preference: str = "均衡"):
    # 1. 查城市坐标
    origin_coord = CITY_COORDS.get(from_city)
    dest_coord = CITY_COORDS.get(to_city)
    if not origin_coord or not dest_coord:
        missing = [c for c, v in {"出发地": from_city, "目的地": to_city}.items() if v not in CITY_COORDS]
        return f"暂不支持{'、'.join(missing)}的交通查询。当前支持：{'、'.join(CITY_COORDS.keys())}"

    # 2. 如有高德 API Key 则调用精确接口
    amap_key = settings.AMAP_API_KEY and not settings.AMAP_API_KEY.startswith("change-me")
    if amap_key:
        try:
            data = await _query_amap_route(settings.AMAP_API_KEY, origin_coord, dest_coord)
            return _format_amap_result(from_city, to_city, data, preference)
        except Exception as e:
            print(f"[WARN] 高德 API 查询失败，降级到规则估算: {e}")

    # 3. 降级：规则估算
    dist = _calc_distance(origin_coord, dest_coord)
    return _estimate_by_rule(from_city, to_city, dist)


def _calc_distance(origin: str, destination: str) -> float:
    """计算两个经纬度坐标之间的直线距离（公里）"""
    o_lat, o_lng = map(float, origin.split(",")[::-1])
    d_lat, d_lng = map(float, destination.split(",")[::-1])

    R = 6371
    dlat = radians(d_lat - o_lat)
    dlng = radians(d_lng - o_lng)
    a = sin(dlat / 2) ** 2 + cos(radians(o_lat)) * cos(radians(d_lat)) * sin(dlng / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


async def _query_amap_route(api_key: str, origin: str, destination: str) -> dict:
    """调用高德驾车路径规划 API"""
    params = {
        "key": api_key,
        "origin": origin,
        "destination": destination,
        "strategy": 0,
        "show_fields": "cost",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://restapi.amap.com/v3/direction/driving",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


def _estimate_by_rule(from_city: str, to_city: str, dist_km: float) -> str:
    """基于距离规则的交通方案估算"""
    # 选推荐交通方式
    recommended = "火车"
    advice = ""
    for lo, hi, mode, desc in DISTANCE_RULES:
        if lo < dist_km <= hi:
            recommended = mode
            advice = desc
            break

    # 估算费用
    high_speed_price = int(dist_km * PRICE_ESTIMATE["高铁"]["基价"])
    flight_price = PRICE_ESTIMATE["飞机"]["基价"]

    result = (
        f"【{from_city} → {to_city} 交通方案 · 参考】\n"
        f"  直线距离：约 {dist_km:.0f} 公里\n"
        f"  推荐方式：{recommended}\n"
        f"  说明：{advice}\n"
        f"\n"
        f"  费用参考（单人）\n"
        f"  · 高铁二等座：约 ¥{high_speed_price}\n"
        f"  · 经济舱机票：约 ¥{flight_price}\n"
        f"  · 自驾（油费+过路费）：约 ¥{int(dist_km * PRICE_ESTIMATE['自驾']['基价'])}\n"
        f"\n"
        f"  ⚠️ 以上为理论估算，实际价格请以购票平台为准"
    )
    return result


def _format_amap_result(from_city: str, to_city: str, data: dict, preference: str) -> str:
    """格式化高德 API 返回结果"""
    if data.get("status") != "1":
        return f"查询路线失败：{data.get('info', '未知错误')}"

    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
        return f"未找到 {from_city} → {to_city} 的驾车路线"

    path = paths[0]
    distance_m = int(path.get("distance", 0))
    duration_s = int(path.get("duration", 0))
    toll = path.get("toll", "0")

    distance_km = round(distance_m / 1000, 1)
    duration_h = duration_s / 3600

    if duration_h >= 1:
        duration_str = f"{int(duration_h)}小时{int(duration_s % 3600 / 60)}分钟"
    else:
        duration_str = f"{int(duration_s / 60)}分钟"

    steps = path.get("steps", [])
    waypoints = []
    for step in steps[:3]:
        instruction = step.get("instruction", "")
        if instruction:
            waypoints.append(instruction)
    waypoint_str = " → ".join(waypoints[:3])
    if len(steps) > 3:
        waypoint_str += "…"

    result = (
        f"【{from_city} → {to_city} 驾车路线】\n"
        f"  全程：约 {distance_km} 公里\n"
        f"  预计用时：{duration_str}\n"
        f"  预估路费：约 ¥{toll}\n"
        f"  途经：{waypoint_str}\n"
        f"\n"
    )

    # 根据偏好加贴士
    if preference == "速度优先" and duration_h > 3:
        result += "  小贴士：驾车时间较长，建议考虑高铁或飞机方案\n"
    elif preference == "经济优先" and int(toll) > 100:
        result += "  小贴士：路费较高，可对比高铁票价\n"
    else:
        suggest_train = distance_km > 300 and distance_km < 1000
        if suggest_train:
            result += f"  小贴士：{distance_km}公里左右路程，高铁也是不错的选择\n"

    return result


transport_guiding_tool = Tool(
    name="transport_guiding",
    description="查询两个城市之间的交通方案，包括距离、耗时、交通方式建议和费用估算",
    parameters=TRANSPORT_PARAMETERS,
    required=["from_city", "to_city"],
    handler=transport_guiding,
)
