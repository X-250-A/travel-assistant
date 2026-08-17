"""Critic 质量审查测试 — 覆盖审查→重生成→降级的完整判定树"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.app.agent.conversation import ConversationManager, ConversationState
from backend.app.agent.planner import TripPlannerAgent

# ─── 测试用的假行程 JSON（v1）─────────────────────────────────────────────
FAKE_TRIP_JSON = json.dumps(
    {
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
    }
)

# v2：重生成后的版本（改了 budget，用于断言「重生成后落库 v2」）
FAKE_TRIP_JSON_V2 = json.dumps(
    {
        "destination": "成都",
        "duration": 3,
        "budget": 2500,
        "style": ["美食", "人文"],
        "overview": "三日成都美食之旅（预算优化版）",
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
                        "suggestion": "奎星楼街吃串串，人均 40",
                        "location_near": "宽窄巷子",
                    }
                ],
            }
        ],
        "overall_tips": "带伞",
    }
)


# ─── 辅助：mock 审查器返回 ────────────────────────────────────────────────
def _mock_critic_response(passed, issues=None, scores=None):
    """构造假的 OpenAI chat.completions.create 返回值（审查器返回）"""
    body = {
        "passed": passed,
        "scores": scores or {"budget": 90, "preferences": 90, "feasibility": 90},
        "issues": issues or [],
    }
    mock_message = MagicMock()
    mock_message.content = json.dumps(body, ensure_ascii=False)
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_stream(chunks):
    """构造一个 async generator mock，按 chunks 逐条输出"""
    s = AsyncMock()
    s.__aiter__.return_value = chunks
    return s


# ─── 关键：patch planner 模块级 settings ──────────────────────────────────
# planner.py 里用的是 `from backend.app.config import settings`（模块级），
# 不是 self.settings。所以必须 patch 模块级 settings，让 CRITIC_ENABLED=True
@pytest.fixture
def critic_on():
    """开启 Critic 审查（patch planner 模块级 settings）"""
    settings_mock = MagicMock()
    settings_mock.CRITIC_ENABLED = True
    settings_mock.CRITIC_MAX_REGENERATE = 1
    settings_mock.DEEPSEEK_MODEL = "deepseek-v4-flash"
    settings_mock.LLM_REQUEST_TIMEOUT = 90
    with patch("backend.app.agent.planner.settings", settings_mock):
        yield settings_mock


# ─── 辅助：构造带 mock LLM 的 Agent ───────────────────────────────────────
def _make_agent(stream_chunks, critic_response=None, classify_intent="new_trip"):
    """返回一个 TripPlannerAgent，LLM 各层已 mock。

    - llm_classify_intent → 指定意图
    - chat → 无 tool_calls（进入 chat_stream 分支）
    - chat_stream → 按 stream_chunks 输出 v1 文本
    - client.chat.completions.create → critic_response（审查器返回；None 则不 mock，
      用于"开关关闭 / 无 plan_data"等断言未被调用的场景）
    """
    agent = TripPlannerAgent()

    mock_msg = MagicMock()
    mock_msg.content = None
    mock_msg.tool_calls = None
    agent.llm_client.chat = AsyncMock(return_value=mock_msg)

    agent.llm_client.chat_stream = MagicMock(return_value=_make_stream(stream_chunks))

    agent.llm_classify_intent = AsyncMock(return_value=classify_intent)
    if critic_response is not None:
        agent.llm_client.client.chat.completions.create = AsyncMock(return_value=critic_response)
    return agent


def _make_agent_with_v2(v1_chunks, v2_chunks, critic_response, classify_intent="new_trip"):
    """重生成场景：chat_stream 按 side_effect 依次返回 v1 流、v2 流"""
    agent = TripPlannerAgent()

    mock_msg = MagicMock()
    mock_msg.content = None
    mock_msg.tool_calls = None
    agent.llm_client.chat = AsyncMock(return_value=mock_msg)

    # 第 1 次 chat_stream = v1 主生成；第 2 次 = v2 重生成
    agent.llm_client.chat_stream = MagicMock(
        side_effect=[
            _make_stream(v1_chunks),
            _make_stream(v2_chunks),
        ]
    )

    agent.llm_classify_intent = AsyncMock(return_value=classify_intent)
    if critic_response is not None:
        agent.llm_client.client.chat.completions.create = AsyncMock(return_value=critic_response)
    return agent


# ─── 辅助：mock Redis 与 ConversationManager（复用 test_planner 模式）──────
def _make_mock_redis(prefs=None):
    """构造能响应偏好功能的 mock Redis。

    load_preferences 调用 hgetall 取偏好，prefs 可传入模拟"用户已有历史偏好"。
    """
    mock_r = AsyncMock()
    mock_r.hgetall = AsyncMock(return_value=prefs or {})
    mock_r.hmset = AsyncMock(return_value=True)
    mock_r.expire = AsyncMock(return_value=True)
    return mock_r


def _make_conversation_manager():
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


def _collect_events(agent, user_input, conv, prefs=None):
    events = []

    async def _run():
        async for event in agent.handle_message(user_input, conv, _make_mock_redis(prefs)):
            events.append(event)

    asyncio.run(_run())
    return events


# ═══════════════════════════════════════════════════════════════════════════
# 审查通过 → 落库原方案（不重生成）
# ═══════════════════════════════════════════════════════════════════════════


class TestCriticPass:
    def test_critic_pass_keeps_original_plan(self, critic_on):
        """审查通过（passed=True）→ 落库原 FAKE_TRIP_JSON，chat_stream 只调 1 次"""
        agent = _make_agent(
            stream_chunks=[FAKE_TRIP_JSON],
            critic_response=_mock_critic_response(passed=True),
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # 落库的是原方案（budget 3000，不是 v2 的 2500）
        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 3000

        # chat_stream 只调 1 次（v1 主生成，无重生成）
        agent.llm_client.chat_stream.assert_called_once()

        # 有审查 thinking，但无「重新生成」thinking
        thinkings = [e for e in events if e["type"] == "thinking"]
        assert any("质量审查" in t["content"] for t in thinkings)
        assert not any("重新生成" in t["content"] for t in thinkings)
        assert events[-1]["type"] == "done"


# ═══════════════════════════════════════════════════════════════════════════
# 审查不达标 → 重生成一次，落库 v2
# ═══════════════════════════════════════════════════════════════════════════


class TestCriticRegenerate:
    def test_critic_fail_regenerates_once(self, critic_on):
        """审查不达标 + issues 非空 → 重生成一次，落库 v2，chat_stream 恰好 2 次"""
        agent = _make_agent_with_v2(
            v1_chunks=[FAKE_TRIP_JSON],
            v2_chunks=[FAKE_TRIP_JSON_V2],
            critic_response=_mock_critic_response(
                passed=False,
                issues=["预算超支", "第2天安排过满"],
            ),
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # 落库 v2（budget 2500 说明是重生成版）
        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 2500

        # chat_stream 恰好 2 次：v1 + v2 重生成
        assert agent.llm_client.chat_stream.call_count == 2

        # 有「重新生成」thinking
        thinkings = [e for e in events if e["type"] == "thinking"]
        assert any("重新生成" in t["content"] for t in thinkings)
        assert events[-1]["type"] == "done"

    def test_critic_self_contradictory_forces_regenerate(self, critic_on):
        """审查自相矛盾（passed=True 但 issues 非空）→ 防御逻辑强制按不达标处理，触发重生成"""
        # _mock_critic_response(passed=True, issues=[...]) 会返回 passed=True + issues 非空
        agent = _make_agent_with_v2(
            v1_chunks=[FAKE_TRIP_JSON],
            v2_chunks=[FAKE_TRIP_JSON_V2],
            critic_response=_mock_critic_response(
                passed=True,  # 自相矛盾：说通过却给了修正项
                issues=["预算超支"],
            ),
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # 防御逻辑应强制 passed=False → 触发重生成 → 落库 v2
        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 2500
        # chat_stream 恰好 2 次：v1 + v2 重生成
        assert agent.llm_client.chat_stream.call_count == 2
        assert events[-1]["type"] == "done"

    def test_critic_second_version_bad_json_stops_loop(self, critic_on):
        """重生成无合法 JSON → 落库 v1，且不进入第 2 次重生成（防无限循环）"""
        agent = _make_agent_with_v2(
            v1_chunks=[FAKE_TRIP_JSON],
            v2_chunks=["抱歉，我调整了一下预算，但没有生成完整 JSON"],
            critic_response=_mock_critic_response(
                passed=False,
                issues=["预算超支"],
            ),
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # chat_stream 恰好 2 次：v1 + 1 次重生成（CRITIC_MAX_REGENERATE=1，不再循环）
        assert agent.llm_client.chat_stream.call_count == 2

        # v2 无合法 JSON → 保持 v1
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 3000
        assert events[-1]["type"] == "done"


# ═══════════════════════════════════════════════════════════════════════════
# 降级路径：审查失败 / 返回非法值 → 用原方案，流程不崩
# ═══════════════════════════════════════════════════════════════════════════


class TestCriticDegrade:
    def test_critic_llm_error_degrades(self, critic_on):
        """审查 LLM 抛异常 → 降级用原方案，无「重新生成」thinking，流程正常 done"""
        agent = _make_agent(
            stream_chunks=[FAKE_TRIP_JSON],
            critic_response=_mock_critic_response(passed=True),
        )
        # 让审查 create 抛异常（_ask_critic 内部 try/except → 返回 None → 判定树跳过）
        agent.llm_client.client.chat.completions.create = AsyncMock(
            side_effect=Exception("网络错误")
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # 落库原方案
        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 3000

        # 无「重新生成」thinking（审查失败直接降级）
        thinkings = [e for e in events if e["type"] == "thinking"]
        assert not any("重新生成" in t["content"] for t in thinkings)
        assert events[-1]["type"] == "done"

    def test_critic_invalid_json_degrades(self, critic_on):
        """审查返回非 JSON 字符串 → 解析失败降级用原方案"""
        mock_message = MagicMock()
        mock_message.content = "这不是JSON"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        agent = _make_agent(
            stream_chunks=[FAKE_TRIP_JSON],
            critic_response=mock_response,
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["budget"] == 3000
        assert events[-1]["type"] == "done"


# ═══════════════════════════════════════════════════════════════════════════
# 开关与边界：CRITIC_ENABLED 关闭 / 无 plan_data → 不触发审查
# ═══════════════════════════════════════════════════════════════════════════


class TestCriticGuard:
    def test_critic_disabled_skips_entirely(self):
        """CRITIC_ENABLED=False → 审查 create 永不调用，无审查 thinking"""
        settings_mock = MagicMock()
        settings_mock.CRITIC_ENABLED = False
        settings_mock.CRITIC_MAX_REGENERATE = 1
        settings_mock.DEEPSEEK_MODEL = "deepseek-v4-flash"
        settings_mock.LLM_REQUEST_TIMEOUT = 90

        agent = _make_agent(stream_chunks=[FAKE_TRIP_JSON])
        create_mock = AsyncMock(return_value=_mock_critic_response(passed=True))
        agent.llm_client.client.chat.completions.create = create_mock
        conv = _make_conversation_manager()

        with (
            patch("backend.app.agent.planner.settings", settings_mock),
            patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock),
        ):
            events = _collect_events(agent, "想去成都玩三天", conv)

        create_mock.assert_not_called()
        thinkings = [e for e in events if e["type"] == "thinking"]
        assert not any("质量审查" in t["content"] for t in thinkings)
        assert events[-1]["type"] == "done"

    def test_critic_no_plan_data_skips(self, critic_on):
        """LLM 未产出合法 JSON（plan_data=None）→ 审查 create 永不调用"""
        agent = _make_agent(
            stream_chunks=["很抱歉，我暂时无法为您规划行程。"],
            critic_response=_mock_critic_response(passed=True),
        )
        conv = _make_conversation_manager()

        with patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update:
            events = _collect_events(agent, "想去成都玩三天", conv)

        # 无 JSON → plan_data=None → 不审查、不落库
        mock_update.assert_not_called()
        agent.llm_client.client.chat.completions.create.assert_not_called()
        assert events[-1]["type"] == "done"


# ═══════════════════════════════════════════════════════════════════════════
# modify_trip 修改方案也走审查
# ═══════════════════════════════════════════════════════════════════════════


class TestCriticModify:
    def test_critic_runs_on_modify_trip(self, critic_on):
        """modify_trip 修改方案 → 审查 create 被调用一次，落库修改后方案"""
        agent = _make_agent(
            stream_chunks=[
                "把行程改成四天：\n"
                + json.dumps({"destination": "成都", "duration": 4, "budget": 3000})
            ],
            critic_response=_mock_critic_response(passed=True),
            classify_intent="modify_trip",
        )
        conv = _make_conversation_manager()

        with (
            patch(
                "backend.app.agent.planner.find_trip_by_id",
                new_callable=AsyncMock,
                return_value=MagicMock(plan_data=json.loads(FAKE_TRIP_JSON)),
            ),
            patch("backend.app.agent.planner.update_trip", new_callable=AsyncMock) as mock_update,
        ):
            events = _collect_events(agent, "把行程改成四天", conv)

        # 审查被调用（modify 也走审查）
        agent.llm_client.client.chat.completions.create.assert_called_once()
        # 落库修改后方案
        mock_update.assert_called_once()
        saved_plan = mock_update.call_args.kwargs["plan_data"]
        assert saved_plan["duration"] == 4
        assert events[-1]["type"] == "done"


# ═══════════════════════════════════════════════════════════════════════════
# 审查输入构造验证：messages 应包含 critic 人设 + 需求 + 偏好 + 行程 JSON
# ═══════════════════════════════════════════════════════════════════════════


class TestAskCriticMessages:
    def test_ask_critic_sends_plan_and_prefs(self, critic_on):
        agent = _make_agent(
            stream_chunks=[FAKE_TRIP_JSON],
            critic_response=_mock_critic_response(passed=True),
        )
        conv = _make_conversation_manager()

        # 注意：handle_message 开头会用 load_preferences 覆盖 conv.pref，
        # 所以偏好要通过 mock Redis 的 hgetall 返回，而不是直接设 conv.pref
        _collect_events(
            agent,
            "我不吃辣，预算3000，想去成都玩三天",
            conv,
            prefs={"饮食": "忌口辣", "预算": "上限3000元"},
        )

        create_mock = agent.llm_client.client.chat.completions.create
        call_args = create_mock.call_args
        messages = call_args.kwargs["messages"]

        # system = critic 人设（含"审查"关键词）
        assert messages[0]["role"] == "system"
        assert "审查" in messages[0]["content"]

        # user = 需求 + 偏好 + JSON
        user_content = messages[1]["content"]
        assert "预算" in user_content  # 用户需求
        assert "忌口辣" in user_content  # 偏好被渲染进去
        assert "宽窄巷子" in user_content  # 行程 JSON 被注入

        # 调用参数正确
        assert call_args.kwargs["temperature"] == 0
        assert call_args.kwargs["response_format"] == {"type": "json_object"}
