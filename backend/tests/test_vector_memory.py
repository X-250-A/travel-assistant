"""向量记忆纯逻辑测试 — cosine_similarity + save_vector_memory + recall_vector_memory

覆盖三件事（都不碰真实 API / Redis）：
- cosine_similarity：数学正确性（同向/垂直/反向/零向量/正交）
- save_vector_memory：rpush + json 序列化
- recall_vector_memory：KNN 全量遍历 → 阈值过滤 → 排序 → topk 截断
"""

import json
from unittest.mock import AsyncMock

import pytest
from backend.app.memory.vector_memory import (
    cosine_similarity,
    recall_vector_memory,
    save_vector_memory,
)

# ─── 手工构造的低维假向量（3 维，便于手动验算） ────────────────────────────


def _vec(*coords):
    return list(coords)


class TestCosineSimilarity:
    """余弦相似度数学正确性"""

    def test_identical_vectors(self):
        """完全相同的向量 → 1.0（同向）"""
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_parallel_vectors(self):
        """同向不同长度 → 1.0（余弦只关心方向，不关心模长）"""
        assert cosine_similarity([1, 0, 0], [3, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """垂直向量 → 0.0（点积为 0）"""
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """反向向量 → -1.0"""
        assert cosine_similarity([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)

    def test_similar_less_than_identical(self):
        """有夹角的向量相似度低于同向"""
        identical = cosine_similarity([1, 1, 0], [1, 1, 0])
        angled = cosine_similarity([1, 1, 0], [1, 0, 0])
        assert identical > angled

    def test_zero_vector_returns_zero(self):
        """零向量无方向 → 相似度定为 0，不抛 ZeroDivisionError"""
        assert cosine_similarity([0, 0, 0], [1, 0, 0]) == 0.0
        assert cosine_similarity([1, 0, 0], [0, 0, 0]) == 0.0

    def test_order_does_not_matter(self):
        """对称性：cosine(a, b) == cosine(b, a)"""
        a, b = [1, 2, 3], [3, 1, 2]
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


def _mock_redis_with(items: list[str]) -> AsyncMock:
    """构造 mock Redis，lrange 返回给定 json 字符串列表"""
    mock_r = AsyncMock()
    mock_r.lrange = AsyncMock(return_value=items)
    return mock_r


def _mem_json(text: str, vector: list[float]) -> str:
    return json.dumps({"text": text, "vector": vector})


class TestSaveVectorMemory:
    @pytest.mark.asyncio
    async def test_save_rpushes_json(self):
        """保存 → 调用 rpush 且内容为 JSON（含 text 和 vector）"""
        mock_r = AsyncMock()
        await save_vector_memory(mock_r, 42, "上次去成都嫌人多", [0.1, 0.2])

        mock_r.rpush.assert_called_once()
        key = mock_r.rpush.call_args.args[0]
        payload = mock_r.rpush.call_args.args[1]
        assert key == "user:memories:42"
        assert json.loads(payload) == {
            "text": "上次去成都嫌人多",
            "vector": [0.1, 0.2],
        }


class TestRecallVectorMemory:
    """KNN 检索：阈值过滤 → 相似度排序 → topk 截断"""

    @pytest.mark.asyncio
    async def test_recalls_most_similar_above_threshold(self):
        """查询"推荐火锅" → 召回"喜欢火锅"（相似度最高）排第一"""
        # 3 维假向量：火锅方向偏 [1,0,0]，辣的反方向偏 [-1,0,0]，天气方向偏 [0,1,0]
        items = [
            _mem_json("喜欢火锅", [1.0, 0.1, 0.0]),
            _mem_json("讨厌辣", [-0.9, 0.1, 0.0]),
            _mem_json("想看雪", [0.0, 0.9, 0.1]),
        ]
        mock_r = _mock_redis_with(items)
        query = [1.0, 0.0, 0.0]  # "推荐火锅店" 的查询向量

        result = await recall_vector_memory(mock_r, 42, query, topk=3, threshold=0.0)

        assert result[0] == "喜欢火锅"  # 最相似，排第一
        # 排序正确性：火锅 > 想看雪；讨厌辣（余弦 -0.9）低于阈值 0.0 被过滤
        # 火锅 cos≈1.0，想看雪 cos=0.0（正交），讨厌辣 cos=-0.9（反向最低）
        assert result == ["喜欢火锅", "想看雪"]

    @pytest.mark.asyncio
    async def test_threshold_filters_below(self):
        """低于阈值的记忆被过滤掉"""
        items = [
            _mem_json("喜欢火锅", [1.0, 0.0, 0.0]),
            _mem_json("想看雪", [0.0, 1.0, 0.0]),
        ]
        mock_r = _mock_redis_with(items)
        query = [1.0, 0.0, 0.0]

        # 高阈值 0.8：只有火锅命中；雪方向查询差 0.8 以上被滤
        result = await recall_vector_memory(mock_r, 42, query, topk=3, threshold=0.8)
        assert result == ["喜欢火锅"]

        # 零阈值：两条都返回
        result = await recall_vector_memory(mock_r, 42, query, topk=3, threshold=0.0)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_topk_limits_results(self):
        """topk=1 → 只返回最相似的一条"""
        items = [
            _mem_json("喜欢火锅", [1.0, 0.0, 0.0]),
            _mem_json("喜欢川菜", [0.95, 0.1, 0.0]),
        ]
        mock_r = _mock_redis_with(items)
        query = [1.0, 0.0, 0.0]

        result = await recall_vector_memory(mock_r, 42, query, topk=1, threshold=0.0)
        assert result == ["喜欢火锅"]  # 火锅比川菜更接近查询

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty(self):
        """无任何记忆 → 返回空列表"""
        mock_r = _mock_redis_with([])
        result = await recall_vector_memory(mock_r, 42, [1.0, 0.0, 0.0], topk=3, threshold=0.0)
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_user_scoped_key(self):
        """检索只查当前用户的 key"""
        mock_r = _mock_redis_with([])
        await recall_vector_memory(mock_r, 42, [1.0, 0.0, 0.0], topk=3, threshold=0.0)
        mock_r.lrange.assert_called_once_with("user:memories:42", 0, -1)
