"""行程规划 Agent 测试 — _keyword_classify + llm_classify_intent + handle_message（mock LLM）"""

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

# ─── LLM 分类返回的假响应 ─────────────────────────────────────────────────
FAKE_CLASSIFY_NEW_TRIP = json.dumps({"intent": "new_trip", "reason": "用户表达了旅行意愿"})
FAKE_CLASSIFY_MODIFY = json.dumps({"intent": "modify_trip", "reason": "用户想修改行程"})
FAKE_CLASSIFY_QUESTION = json.dumps({"intent": "ask_question", "reason": "用户提出了一个知识性问题"})
FAKE_CLASSIFY_UNCLEAR = json.dumps({"intent": "unclear", "reason": "用户输入过于模糊"})


# ─── 辅助：创建一个带 mock LLM 的 Agent ──────────────────────────────────
def _make_agent(stream_chunks: list[str]) -> TripPlannerAgent:
    """返回一个 TripPlannerAgent，其内部的 LLMClient.chat / chat_stream / llm_classify_intent 已被 mock"""
    agent = TripPlannerAgent()

    # mock 非流式 chat：返回一个无 tool_calls 的消息，让流程进入 chat_stream 分支
    mock_msg = MagicMock()
    mock_msg.content = None
    mock_msg.tool_calls = None
    agent.llm_client.chat = AsyncMock(return_value=mock_msg)

    # mock 流式 chat_stream：按 chunks 逐条输出
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = stream_chunks
    agent.llm_client.chat_stream = MagicMock(return_value=mock_stream)

    # 默认 mock 意图分类为 unclear（各测试可按需覆盖）
    agent.llm_classify_intent = AsyncMock(return_value="unclear")
    return agent


# ─── 辅助：mock LLM 分类请求的返回值 ─────────────────────────────────────
def _mock_classify_response(intent: str) -> MagicMock:
    """构造一个假的 OpenAI chat.completions.create 返回值"""
    mock_message = MagicMock()
    mock_message.content = json.dumps({"intent": intent, "reason": "mock"})
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


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
# 关键词分类测试（纯逻辑，不依赖外部资源）
# ═══════════════════════════════════════════════════════════════════════════

class TestKeywordClassify:

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
        assert agent._keyword_classify(text) == expected

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
        assert agent._keyword_classify(text) == expected

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
        assert agent._keyword_classify(text) == expected

    @pytest.mark.parametrize("text", [
        "你好",
        "谢谢",
        "好的",
        "",
    ])
    def test_unclear(self, text):
        agent = TripPlannerAgent()
        assert agent._keyword_classify(text) == "unclear"

    def test_modify_takes_priority_over_new(self):
        """修改关键词优先于新建（同时包含时，先匹配 modify）"""
        agent = TripPlannerAgent()
        # "调整" 在 modified_keywords 里，"规划" 在 new_keywords 里
        assert agent._keyword_classify("调整一下去成都的规划") == "modify_trip"

    def test_new_takes_priority_over_question(self):
        """新建关键词优先于提问（同时包含时，先匹配 new）"""
        agent = TripPlannerAgent()
        # "想去" 在 new_keywords，"怎么样" 在 question_keywords
        assert agent._keyword_classify("想去成都，怎么样？") == "new_trip"


# ═══════════════════════════════════════════════════════════════════════════
# LLM 意图分类测试（mock OpenAI client）
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMClassifyIntent:

    @pytest.mark.asyncio
    async def test_classify_new_trip(self):
        """LLM 返回 new_trip → 分类正确"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        agent.llm_client.client.chat.completions.create = AsyncMock(
            return_value=_mock_classify_response("new_trip")
        )
        result = await agent.llm_classify_intent("我想去北京玩", conv)
        assert result == "new_trip"

    @pytest.mark.asyncio
    async def test_classify_modify_trip(self):
        """LLM 返回 modify_trip → 分类正确"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        agent.llm_client.client.chat.completions.create = AsyncMock(
            return_value=_mock_classify_response("modify_trip")
        )
        result = await agent.llm_classify_intent("把第二天改一下", conv)
        assert result == "modify_trip"

    @pytest.mark.asyncio
    async def test_classify_ask_question(self):
        """LLM 返回 ask_question → 分类正确"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        agent.llm_client.client.chat.completions.create = AsyncMock(
            return_value=_mock_classify_response("ask_question")
        )
        result = await agent.llm_classify_intent("成都有什么好吃的？", conv)
        assert result == "ask_question"

    @pytest.mark.asyncio
    async def test_classify_unclear(self):
        """LLM 返回 unclear → 分类正确"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        agent.llm_client.client.chat.completions.create = AsyncMock(
            return_value=_mock_classify_response("unclear")
        )
        result = await agent.llm_classify_intent("嗯嗯", conv)
        assert result == "unclear"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        """LLM 调用失败 → 回退到关键词匹配"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        # 模拟 LLM 调用抛出异常
        agent.llm_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("网络错误")
        )
        # 关键词匹配："想去" 命中 new_trip
        result = await agent.llm_classify_intent("想去成都", conv)
        assert result == "new_trip"

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_intent(self):
        """LLM 返回不在四分类中的值 → 归为 unclear"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        agent.llm_client.client.chat.completions.create = AsyncMock(
            return_value=_mock_classify_response("book_hotel")  # 不在四分类中
        )
        result = await agent.llm_classify_intent("帮我订个酒店", conv)
        assert result == "unclear"

    @pytest.mark.asyncio
    async def test_classify_with_context_new_trip(self):
        """新行程（trip_id=0）→ 不注入上下文提示"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        conv.trip_id = 0  # 无已有行程

        create_mock = AsyncMock(return_value=_mock_classify_response("new_trip"))
        agent.llm_client.client.chat.completions.create = create_mock

        result = await agent.llm_classify_intent("想去成都", conv)
        assert result == "new_trip"

        # 验证传给 LLM 的 messages 中没有上下文提示
        call_args = create_mock.call_args
        messages = call_args.kwargs["messages"]
        # 应该只有 system + user，没有额外的 context_hint
        assert len(messages) == 2  # system prompt + user input

    @pytest.mark.asyncio
    async def test_classify_with_context_existing_trip(self):
        """已有行程（trip_id≠0）→ 注入上下文提示"""
        agent = TripPlannerAgent()
        conv = _make_conversation_manager()
        conv.trip_id = 5
        conv.state = ConversationState.PLANNING

        create_mock = AsyncMock(return_value=_mock_classify_response("modify_trip"))
        agent.llm_client.client.chat.completions.create = create_mock

        result = await agent.llm_classify_intent("换个景点", conv)
        assert result == "modify_trip"

        # 验证传给 LLM 的 messages 中包含了上下文提示
        call_args = create_mock.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 3  # system prompt + context hint + user input
        assert "modify_trip" in messages[1]["content"]


# ═══════════════════════════════════════════════════════════════════════════
# handle_message 测试（mock LLM）
# ═══════════════════════════════════════════════════════════════════════════

class TestHandleMessage:

    @pytest.mark.asyncio
    async def test_handle_unclear_intent(self):
        """意图不明时返回引导语，不发 token"""
        agent = _make_agent([])
        # _make_agent 默认 mock llm_classify_intent 返回 "unclear"
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
        agent.llm_classify_intent = AsyncMock(return_value="new_trip")
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
        agent.llm_classify_intent = AsyncMock(return_value="new_trip")
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
        agent.llm_classify_intent = AsyncMock(return_value="new_trip")
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
        agent.llm_classify_intent = AsyncMock(return_value="modify_trip")
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
        agent.llm_classify_intent = AsyncMock(return_value="modify_trip")
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
        agent.llm_classify_intent = AsyncMock(return_value="modify_trip")
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
