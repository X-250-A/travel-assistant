"""
测试向量记忆的 embedding 客户端（services/embedding.py）

覆盖三条线：
- available()：无 key 降级判断（含 change-me → False）
- 构造：AsyncOpenAI 收到正确的 base_url / api_key / http_client
- embed()：批量文本 → 批量向量；model / input 正确传递

所有测试全 mock，不真打 SiliconFlow、不真建连接（patch 掉 httpx.AsyncClient 与 AsyncOpenAI）。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.app.services import embedding as embedding_module
from backend.app.services.embedding import EmbeddingClient

# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_openai():
    """patch 掉 AsyncOpenAI / httpx.AsyncClient 构造，返回可控的 mock client"""
    with (
        patch.object(embedding_module.httpx, "AsyncClient") as mock_http,
        patch.object(embedding_module, "AsyncOpenAI") as mock_openai_cls,
    ):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        yield mock_openai_cls, mock_client, mock_http


def _fake_response(*vectors):
    """构造 openai embeddings.create 的响应：data 里每个 item 带 embedding"""
    return SimpleNamespace(data=[SimpleNamespace(embedding=list(v)) for v in vectors])


# ── available() 降级判断 ───────────────────────────────────────────────────


def test_available_false_when_key_has_change_me(mock_openai):
    """key 含 change-me（未配置）→ False，整条链路应静默跳过"""
    with patch.object(
        embedding_module.settings, "SILICONFLOW_API_KEY", "sk-test-dummy-key-change-me"
    ):
        assert EmbeddingClient().available() is False


def test_available_true_when_key_configured(mock_openai):
    """key 已配置（不含 change-me）→ True"""
    with patch.object(embedding_module.settings, "SILICONFLOW_API_KEY", "sk-real-siliconflow-key"):
        assert EmbeddingClient().available() is True


# ── 构造：配置传递 ─────────────────────────────────────────────────────────


def test_constructor_passes_siliconflow_config(mock_openai):
    """构造时 AsyncOpenAI 收到 settings 里的 base_url / api_key，并传入自定义 http_client"""
    mock_openai_cls, _, mock_http = mock_openai
    mock_http.return_value = MagicMock()  # httpx.AsyncClient 返回 mock，避免真建连接池

    with (
        patch.object(
            embedding_module.settings, "SILICONFLOW_BASE_URL", "https://custom.example.com/v1"
        ),
        patch.object(embedding_module.settings, "SILICONFLOW_API_KEY", "sk-real-siliconflow-key"),
    ):
        client = EmbeddingClient()

    kwargs = mock_openai_cls.call_args.kwargs
    assert kwargs["base_url"] == "https://custom.example.com/v1"
    assert kwargs["api_key"] == "sk-real-siliconflow-key"
    assert kwargs["http_client"] is mock_http.return_value  # 传的是项目自己的超时配置客户端
    assert client.model == embedding_module.settings.SILICONFLOW_EMBEDDING_MODEL


# ── embed() 核心逻辑 ───────────────────────────────────────────────────────


async def test_embed_returns_batch_embeddings(mock_openai):
    """批量文本 → 返回等长向量列表，create 收到 model + 完整 input"""
    _, mock_client, _ = mock_openai
    mock_client.embeddings.create = AsyncMock(
        return_value=_fake_response([0.1, 0.2], [0.3, 0.4], [0.5, 0.6])
    )

    result = await EmbeddingClient().embed(["成都", "杭州", "上海"])

    assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    # openai SDK 的 embeddings.create 用关键字参数调用，断言在 kwargs 里
    mock_client.embeddings.create.assert_awaited_once_with(
        model="BAAI/bge-m3",
        input=["成都", "杭州", "上海"],
    )


async def test_embed_single_text_returns_single_vector(mock_openai):
    """单条文本 → 返回长度 1 的列表"""
    _, mock_client, _ = mock_openai
    mock_client.embeddings.create = AsyncMock(return_value=_fake_response([0.1]))

    result = await EmbeddingClient().embed(["想去成都"])

    assert len(result) == 1
    assert result[0] == [0.1]


async def test_embed_empty_input_returns_empty(mock_openai):
    """空列表入参 → 返回空列表，不崩"""
    _, mock_client, _ = mock_openai
    mock_client.embeddings.create = AsyncMock(return_value=_fake_response())

    result = await EmbeddingClient().embed([])

    assert result == []
    mock_client.embeddings.create.assert_awaited_once_with(model="BAAI/bge-m3", input=[])
