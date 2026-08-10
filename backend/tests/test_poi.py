"""
测试 POI 景点查询工具（tools/poi.py）

覆盖两条线：
- format_pois 纯函数：格式化、兜底、limit 截断
- search_poi 完整流程：无 key 降级 / 缓存命中 / 高德正常 / 高德网络异常 / 高德业务失败

所有测试全 mock，不真打高德 API、不真连 Redis（conftest 的 autouse mock_redis 已 patch get_redis）。
"""
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.tools import poi as poi_module
from backend.app.tools.poi import search_poi, format_pois


# ── 假数据 ────────────────────────────────────────────────────────────────

FAKE_POIS = [
    {
        "name": "宽窄巷子",
        "type": "风景名胜;风景名胜;国家级景点",
        "address": "青羊区长顺街",
        "biz_ext": {"rating": "4.5", "cost": "0"},
    },
    {
        "name": "武侯祠",
        "type": "文化古迹;文化古迹;省级景点",
        "address": "武侯区武侯祠大街",
        "biz_ext": {"rating": "4.6", "cost": "50"},
    },
    {
        # 故意缺失 biz_ext，验证兜底
        "name": "无名景点",
        "type": None,
        "address": None,
    },
]

AMAP_SUCCESS = {"status": "1", "pois": FAKE_POIS}
AMAP_FAILURE = {"status": "0", "info": "INVALID_USER_KEY"}


def _mock_amap_client(payload: dict):
    """构造一个 mock 的高德 HTTP 客户端：async with 上下文 + await get() 返回 payload"""
    resp = MagicMock()
    resp.json.return_value = payload
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)   # await client.get() → resp
    ctx = MagicMock()
    ctx.__aenter__.return_value = client
    ctx.__aexit__.return_value = None
    return client, ctx


# ── format_pois 纯函数 ────────────────────────────────────────────────────

def test_format_pois_basic():
    """正常格式化：编号、名称、类型（取分号第一段）、评分、门票、地址"""
    result = format_pois(FAKE_POIS[:2], "成都", 10)
    assert "成都" in result
    assert "1·宽窄巷子" in result
    assert "风景名胜" in result          # type 取分号第一段，不带完整串
    assert "评分4.5" in result
    assert "费用0" in result            # 门票是"费用"字样
    assert "武侯祠" in result


def test_format_pois_limit_truncates():
    """limit 截断：只格式化前 limit 个"""
    result = format_pois(FAKE_POIS, "成都", 2)
    assert "3·" not in result           # 只到第 2 个
    assert "2·武侯祠" in result


def test_format_pois_missing_fields_fallback():
    """缺失字段兜底：biz_ext / type / address 缺失不崩"""
    result = format_pois(FAKE_POIS[2:3], "成都", 10)
    assert "无名景点" in result
    assert "其他" in result              # type 缺失 → 其他
    assert "暂无" in result              # 评分缺失 → 暂无
    assert "0" in result                # 门票缺失 → 0


def test_format_pois_empty():
    """空列表：只返回标题行，不崩"""
    result = format_pois([], "成都", 10)
    assert "成都" in result
    assert "\n" not in result


# ── search_poi 完整流程 ───────────────────────────────────────────────────

async def test_search_poi_no_key_degradation(mock_redis):
    """无 key 降级：AMAP_API_KEY 含 change-me → 返回提示，不调 API 不碰 Redis"""
    with patch.object(poi_module.settings, "AMAP_API_KEY", "change-me-to-a-amap-api-key"):
        result = await search_poi("成都")
    assert result == "暂未配置景点查询服务"


async def test_search_poi_cache_hit(mock_redis):
    """缓存命中：Redis 返回缓存 → 直接返回，不调高德"""
    mock_redis.get = AsyncMock(return_value="【成都 · 景点】（缓存）")
    with patch.object(poi_module, "httpx") as mock_httpx:
        result = await search_poi("成都")
    assert result == "【成都 · 景点】（缓存）"
    mock_httpx.AsyncClient.assert_not_called()  # 未打高德


async def test_search_poi_success(mock_redis):
    """正常流程：缓存未命中 → 调高德 → 格式化 → 写缓存"""
    mock_redis.get = AsyncMock(return_value=None)  # 未命中
    client, ctx = _mock_amap_client(AMAP_SUCCESS)

    with patch.object(poi_module, "httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = ctx
        result = await search_poi("成都")

    assert "宽窄巷子" in result
    assert "武侯祠" in result
    client.get.assert_called_once()                  # 打了高德
    mock_redis.setex.assert_called_once()            # 写了缓存


async def test_search_poi_amap_network_error(mock_redis):
    """高德网络异常：httpx 抛异常 → 返回友好文案，不崩"""
    mock_redis.get = AsyncMock(return_value=None)
    client, ctx = _mock_amap_client(AMAP_SUCCESS)
    client.get.side_effect = Exception("connection refused")

    with patch.object(poi_module, "httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = ctx
        result = await search_poi("成都")

    assert result == "景点查询暂时不可用，请稍后再试"


async def test_search_poi_amap_business_failure(mock_redis):
    """高德业务失败：status != 1 → 透传高德错误信息"""
    mock_redis.get = AsyncMock(return_value=None)
    client, ctx = _mock_amap_client(AMAP_FAILURE)

    with patch.object(poi_module, "httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = ctx
        result = await search_poi("成都")

    assert "INVALID_USER_KEY" in result
