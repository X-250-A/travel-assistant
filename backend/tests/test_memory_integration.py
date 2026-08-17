"""向量记忆集成测试 — planner 接入（recall 注入 + save 链路 + 降级）

复用 test_planner/test_critic 的 mock 模式：
- TripPlannerAgent 的 llm_client / chat_stream 全 mock
- embedding_client 的 available / embed 手动 mock
- recall_vector_memory / save_vector_memory 在 planner 模块级 patch

save 链路直接测 _save_memory 方法（不经过 handle_message）：
- 因为 _save_memory 和 _generate_plan 共用 self.llm_client.chat，
  走 handle_message 会让 chat 的 mock 干扰主流程。直接测方法则 chat mock 只影响提取。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.app.agent.conversation import ConversationManager, ConversationState
from backend.app.agent.planner import TripPlannerAgent

# ─── 辅助：mock Agent / ConversationManager / Redis ─────────────────────────


def _make_agent(stream_chunks, classify_intent="new_trip"):
    """返回 TripPlannerAgent，LLM 各层 + embedding_client 已 mock"""
    agent = TripPlannerAgent()

    mock_msg = MagicMock()
    mock_msg.content = None
    mock_msg.tool_calls = None
    agent.llm_client.chat = AsyncMock(return_value=mock_msg)

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = stream_chunks
    agent.llm_client.chat_stream = MagicMock(return_value=mock_stream)

    agent.llm_classify_intent = AsyncMock(return_value=classify_intent)

    # embedding_client：默认 available()=False（降级），embed 不真打 API
    agent.embedding_client.available = MagicMock(return_value=False)
    agent.embedding_client.embed = AsyncMock(return_value=[[1.0, 0.0, 0.0]])
    return agent


def _make_conversation_manager():
    """最小化 ConversationManager，绕过数据库"""
    mgr = ConversationManager.__new__(ConversationManager)
    mgr.db = MagicMock()
    mgr.trip_id = 1
    mgr.user_id = 1
    mgr.state = ConversationState.IDLE
    mgr.history_cache = []
    mgr.pref = {}
    mgr.memories = []
    mgr.add_message = AsyncMock()
    mgr.get_context = AsyncMock(
        return_value=[
            {"role": "user", "content": "我想去成都玩三天"},
        ]
    )
    return mgr


def _make_mock_redis():
    mock_r = AsyncMock()
    mock_r.hgetall = AsyncMock(return_value={})
    mock_r.hmset = AsyncMock(return_value=True)
    mock_r.expire = AsyncMock(return_value=True)
    return mock_r


async def _collect_events(agent, user_input, conv, mock_r):
    events = []
    async for event in agent.handle_message(user_input, conv, mock_r):
        events.append(event)
    return events


# ═══════════════════════════════════════════════════════════════════════════
# RECALL：降级关闭 / 召回注入 / 空召回 / 记忆进 build_messages
# ═══════════════════════════════════════════════════════════════════════════


class TestRecall:
    @pytest.mark.asyncio
    async def test_recall_disabled_skips_embedding(self):
        """available()=False → 不调 embed、不调 recall，conversation.memories 保持空"""
        agent = _make_agent(['{"destination": "成都"}'])
        agent.llm_classify_intent = AsyncMock(return_value="unclear")  # 不调 LLM，走引导语分支
        conv = _make_conversation_manager()

        with (
            patch(
                "backend.app.agent.planner.recall_vector_memory", new_callable=AsyncMock
            ) as mock_recall,
            patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock),
        ):
            await _collect_events(agent, "成都怎么样", conv, _make_mock_redis())

        agent.embedding_client.embed.assert_not_called()
        mock_recall.assert_not_called()
        assert conv.memories == []

    @pytest.mark.asyncio
    async def test_recall_enabled_injects_memories(self):
        """available()=True + 召回命中 → conversation.memories 被填充，embed 用当前消息做查询"""
        agent = _make_agent(['{"destination": "成都"}'])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        with patch(
            "backend.app.agent.planner.recall_vector_memory",
            new_callable=AsyncMock,
            return_value=["上次去成都觉得大熊猫基地人太多了"],
        ):
            await _collect_events(agent, "我想去成都玩", conv, _make_mock_redis())

        agent.embedding_client.embed.assert_awaited_once_with(["我想去成都玩"])
        assert conv.memories == ["上次去成都觉得大熊猫基地人太多了"]

    @pytest.mark.asyncio
    async def test_recall_empty_keeps_empty_list(self):
        """召回无结果（空列表）→ conversation.memories 保持空列表，不崩"""
        agent = _make_agent(['{"destination": "成都"}'])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        with patch(
            "backend.app.agent.planner.recall_vector_memory",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await _collect_events(agent, "我想去成都玩", conv, _make_mock_redis())

        assert conv.memories == []

    @pytest.mark.asyncio
    async def test_memories_reach_build_messages(self):
        """召回的记忆要真的进 build_messages，且带 memories 参数"""
        agent = _make_agent(['{"destination": "成都"}'])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        with (
            patch(
                "backend.app.agent.planner.recall_vector_memory",
                new_callable=AsyncMock,
                return_value=["上次去成都嫌人多"],
            ),
            patch(
                "backend.app.agent.planner.PromptBuilder.build_messages",
                return_value=[{"role": "user", "content": "mock"}],
            ) as mock_build,
        ):
            await _collect_events(agent, "我想去成都玩", conv, _make_mock_redis())

        assert mock_build.called
        memories_arg = mock_build.call_args.kwargs.get("memories")
        assert memories_arg == ["上次去成都嫌人多"]


# ═══════════════════════════════════════════════════════════════════════════
# SAVE：直接测 _save_memory（避免 chat 干扰主流程）
# ═══════════════════════════════════════════════════════════════════════════


class TestSave:
    @pytest.mark.asyncio
    async def test_save_disabled_skips(self):
        """available()=False → 不调 LLM 提取、不调 save_vector_memory"""
        agent = _make_agent([])
        conv = _make_conversation_manager()

        with (
            patch(
                "backend.app.agent.planner.save_vector_memory", new_callable=AsyncMock
            ) as mock_save,
            patch.object(agent.llm_client, "chat") as mock_chat,
        ):
            await agent._save_memory("我想去成都玩", conv, _make_mock_redis())

        mock_chat.assert_not_called()
        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_extracts_and_stores(self):
        """available()=True + LLM 返回 should_save=True → embed 批量 + save_vector_memory 逐条存"""
        agent = _make_agent([])
        agent.embedding_client.available = MagicMock(return_value=True)
        agent.embedding_client.embed = AsyncMock(return_value=[[1.0, 0.0], [0.0, 1.0]])
        conv = _make_conversation_manager()

        mock_msg = MagicMock()
        mock_msg.content = json.dumps(
            {
                "should_save": True,
                "facts": ["上次去成都嫌人多", "想避开热门景点"],
            }
        )
        agent.llm_client.chat = AsyncMock(return_value=mock_msg)

        with patch(
            "backend.app.agent.planner.save_vector_memory", new_callable=AsyncMock
        ) as mock_save:
            await agent._save_memory("我想去成都玩，上次去觉得人多", conv, _make_mock_redis())

        agent.embedding_client.embed.assert_awaited_once_with(
            ["上次去成都嫌人多", "想避开热门景点"]
        )
        assert mock_save.call_count == 2
        texts = [c.args[2] for c in mock_save.call_args_list]
        assert texts == ["上次去成都嫌人多", "想避开热门景点"]

    @pytest.mark.asyncio
    async def test_save_when_not_should_save(self):
        """LLM 返回 should_save=False → 不 embed、不存"""
        agent = _make_agent([])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        mock_msg = MagicMock()
        mock_msg.content = json.dumps({"should_save": False, "facts": []})
        agent.llm_client.chat = AsyncMock(return_value=mock_msg)

        with patch(
            "backend.app.agent.planner.save_vector_memory", new_callable=AsyncMock
        ) as mock_save:
            await agent._save_memory("你好", conv, _make_mock_redis())

        agent.embedding_client.embed.assert_not_called()
        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_llm_error_degrades(self):
        """LLM 提取抛异常 → 降级跳过保存，不抛错"""
        agent = _make_agent([])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        agent.llm_client.chat = AsyncMock(side_effect=Exception("网络错误"))

        with patch(
            "backend.app.agent.planner.save_vector_memory", new_callable=AsyncMock
        ) as mock_save:
            # 不应抛异常
            await agent._save_memory("我想去成都玩", conv, _make_mock_redis())

        mock_save.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_invalid_json_degrades(self):
        """LLM 返回非 JSON → json.loads 失败 → 降级跳过，不抛错"""
        agent = _make_agent([])
        agent.embedding_client.available = MagicMock(return_value=True)
        conv = _make_conversation_manager()

        mock_msg = MagicMock()
        mock_msg.content = "这不是JSON"
        agent.llm_client.chat = AsyncMock(return_value=mock_msg)

        with patch(
            "backend.app.agent.planner.save_vector_memory", new_callable=AsyncMock
        ) as mock_save:
            await agent._save_memory("我想去成都玩", conv, _make_mock_redis())

        mock_save.assert_not_called()
