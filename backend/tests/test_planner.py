"""行程规划 Agent 测试 — _classify_intent + handle_message（mock LLM）"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agent.planner import TripPlannerAgent
from backend.app.agent.conversation import ConversationManager, ConversationState


# ─── 测试用的假行程 JSON ──────────────────────────────────────────────────
FAKE_TRIP_JSON = json.dumps({
    "destination": "成都",
    "duration": 3,
    "budget": 3000,
    "style": ["美食", "人文"],
    "overview": "三日成都美食之旅",
    "days": [
        {
            "day": 1,
            "date": None,
            "theme": "市区初探",
            "attractions": [
                {
                    "name": "宽窄巷子",
                    "type": "景点",
                    "duration_minutes": 120,
                    "cost_yuan": 0,
                    "tips": "上午去人少",
                    "transport_from_previous": "无",
                }
            ],
            "meals": [
                {
                    "meal_type": "lunch",
                    "suggestion": "奎星楼街吃串串，人均 50",
                    "location_near": "宽窄巷子",
                }
            ],
        }
    ],
    "overall_tips": "带伞",
})


# ─── 辅助：创建一个带 mock LLM 的 Agent ──────────────────────────────────
def _make_agent(stream_chunks: list[str]) -> TripPlannerAgent:
    """返回一个 TripPlannerAgent，其内部的 LLMClient.chat_stream 已被 mock"""
    agent = TripPlannerAgent()
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = stream_chunks
    agent.llm_client.chat_stream = MagicMock(return_value=mock_stream)
    return agent


# ─── 辅助：创建一个最简单的 ConversationManager（不走数据库）────────────
def _make_conversation_manager() -> ConversationManager:
    """返回一个最小化的 ConversationManager，绕过数据库依赖"""
    mgr = ConversationManager.__new__(ConversationManager)
    mgr.db = MagicMock()
    mgr.trip_id = 1
    mgr.user_id = 1
    mgr.state = ConversationState.IDLE
    mgr.history_cache = []
    mgr.add_message = AsyncMock()
    mgr.get_context = AsyncMock(return_value=[
        {"role": "user", "content": "我想去成都玩三天"},
    ])
    return mgr


# ═══════════════════════════════════════════════════════════════════════════
# 意图分类测试（纯逻辑，不依赖外部资源）
# ═══════════════════════════════════════════════════════════════════════════

class TestClassifyIntent:

    @pytest.mark.parametrize("text,expected", [
        ("帮我规划一次去成都的旅行", "new_trip"),
        ("想去北京玩三天", "new_trip"),
        ("推荐一个三日游", "new_trip"),
        ("安排一次家庭旅游", "new_trip"),
        ("帮我看看南京有什么好玩的", "new_trip"),
        ("旅游去西安", "new_trip"),
        ("旅行到桂林", "new_trip"),
    ])
    def test_new_trip_keywords(self, text, expected):
        agent = TripPlannerAgent()
        assert agent._classify_intent(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("修改第二天的行程", "modify_trip"),
        ("把第三天的景点调整一下", "modify_trip"),
        ("换一个餐厅吧", "modify_trip"),
        ("去掉宽窄巷子", "modify_trip"),
        ("增加一个景点", "modify_trip"),
        ("改成三天", "modify_trip"),
        ("不要这个酒店", "modify_trip"),
        ("换个方案看看", "modify_trip"),
    ])
    def test_modify_trip_keywords(self, text, expected):
        agent = TripPlannerAgent()
        assert agent._classify_intent(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("成都怎么样？", "ask_question"),
        ("有什么好玩的吗？", "ask_question"),
        ("什么是宽窄巷子", "ask_question"),
        ("介绍一下成都", "ask_question"),
        # "如何安排行程比较好" 含 "安排" → new_keywords 优先 → new_trip
        ("如何安排行程比较好", "new_trip"),
    ])
    def test_ask_question_keywords(self, text, expected):
        agent = TripPlannerAgent()
        assert agent._classify_intent(text) == expected

    @pytest.mark.parametrize("text", [
        "你好",
        "谢谢",
        "好的",
        "",
    ])
    def test_unclear(self, text):
        agent = TripPlannerAgent()
        assert agent._classify_intent(text) == "unclear"

    def test_modify_takes_priority_over_new(self):
        """修改关键词优先于新建（同时包含时，先匹配 modify）"""
        agent = TripPlannerAgent()
        # "调整" 在 modified_keywords 里，"规划" 在 new_keywords 里
        assert agent._classify_intent("调整一下去成都的规划") == "modify_trip"

    def test_new_takes_priority_over_question(self):
        """新建关键词优先于提问（同时包含时，先匹配 new）"""
        agent = TripPlannerAgent()
        # "想去" 在 new_keywords，"怎么样" 在 question_keywords
        assert agent._classify_intent("想去成都，怎么样？") == "new_trip"


# ═══════════════════════════════════════════════════════════════════════════
# handle_message 测试（mock LLM）
# ═══════════════════════════════════════════════════════════════════════════

class TestHandleMessage:

    @pytest.mark.asyncio
    async def test_handle_unclear_intent(self):
        """意图不明时返回引导语，不发 token"""
        agent = _make_agent([])
        conv = _make_conversation_manager()

        events = []
        async for event in agent.handle_message("你好", conv):
            events.append(event)

        # 应该只有一条 token + done（没有调用 LLM）
        tokens = [e for e in events if e["type"] == "token"]
        assert len(tokens) == 1
        assert "详细说说" in tokens[0]["content"]
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_new_trip_generates_plan(self):
        """new_trip 意图 → 调 LLM → 输出 token → done"""
        chunks = ['{"destination": "成都"', '}\n']
        agent = _make_agent(chunks)
        conv = _make_conversation_manager()

        events = []
        async for event in agent.handle_message("想去成都玩三天", conv):
            events.append(event)

        # 确认调用了 LLM
        agent.llm_client.chat_stream.assert_called_once()

        # 应该有 token + done
        tokens = [e for e in events if e["type"] == "token"]
        assert len(tokens) == 2
        assert "成都" in "".join(t["content"] for t in tokens)
        assert events[-1]["type"] == "done"

        # 确认保存了用户和 AI 消息
        assert conv.add_message.call_count == 2

    @pytest.mark.asyncio
    async def test_new_trip_saves_parsed_json(self):
        """LLM 返回合法 JSON → 行程被保存"""
        chunks = [FAKE_TRIP_JSON]
        agent = _make_agent(chunks)
        conv = _make_conversation_manager()

        # 用 patch 替换 update_trip 以捕获调用
        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = []
            async for event in agent.handle_message("想去成都玩三天", conv):
                events.append(event)

            mock_update.assert_called_once()

        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_new_trip_json_with_extra_text(self):
        """LLM 在 JSON 前后加了文字 → 正则提取后仍能保存"""
        chunks = ['好的，这是你的行程：\n' + FAKE_TRIP_JSON + '\n祝你旅途愉快！']
        agent = _make_agent(chunks)
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock):
            events = []
            async for event in agent.handle_message("想去成都玩三天", conv):
                events.append(event)

        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_modify_existing_trip(self):
        """修改已有行程 → _apply_feedback 路径"""
        chunks = ['{"destination": "成都", "duration": 4', '}\n']
        agent = _make_agent(chunks)
        conv = _make_conversation_manager()

        with patch(
            "backend.app.agent.planner.find_trip_by_id",
            new_callable=AsyncMock,
            return_value=MagicMock(plan_data=json.loads(FAKE_TRIP_JSON)),
        ):
            events = []
            async for event in agent.handle_message("把第二天的景点改一下", conv):
                events.append(event)

        tokens = [e for e in events if e["type"] == "token"]
        assert len(tokens) >= 1
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_modify_no_plan_data_falls_back_to_generate(self):
        """修改时行程无 plan_data → 回退到生成新方案"""
        chunks = [FAKE_TRIP_JSON]
        agent = _make_agent(chunks)
        conv = _make_conversation_manager()

        with patch(
            "backend.app.agent.planner.find_trip_by_id",
            new_callable=AsyncMock,
            return_value=MagicMock(plan_data=None),
        ):
            events = []
            async for event in agent.handle_message("换个景点吧", conv):
                events.append(event)

        tokens = [e for e in events if e["type"] == "token"]
        # "当前还没有行程方案" 的开场白
        assert any("还没有" in t["content"] for t in tokens)
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_modify_trip_not_found(self):
        """修改时找不到行程 → 静默结束"""
        agent = _make_agent([])
        conv = _make_conversation_manager()

        with patch(
            "backend.app.agent.planner.find_trip_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            events = []
            async for event in agent.handle_message("换个景点吧", conv):
                events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "done"
