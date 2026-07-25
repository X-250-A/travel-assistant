"""聊天接口测试 — POST /api/chat（SSE 流式）"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════════════════════
# 完整请求流程测试（通过 httpx ASGI transport）
# ═══════════════════════════════════════════════════════════════════════════

FAKE_PLAN_JSON = json.dumps({
    "destination": "成都",
    "duration": 3,
    "budget": 3000,
    "style": ["美食"],
    "overview": "三日成都之旅",
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
            "meals": [],
        }
    ],
    "overall_tips": "带伞",
})


async def _collect_sse_events(response) -> tuple[list[dict], str]:
    """解析 SSE 流，返回 (事件列表, 完整文本)"""
    events = []
    full_text_parts = []
    # httpx AsyncClient 用 ASGITransport，可以用 aiter_lines()
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = json.loads(line[len("data: "):])
            events.append(data)
            if data["type"] == "token":
                full_text_parts.append(data["content"])
    return events, "".join(full_text_parts)


class TestChatEndpoint:
    """POST /api/chat — 需要 auth_headers"""

    async def test_chat_new_trip(self, async_client: AsyncClient, auth_headers: str):
        """不传 trip_id → 创建新行程 + SSE 返回"""
        mock_chunks = ['{"destination": "成都"', '}\n']
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = mock_chunks

        mock_llm = MagicMock()
        mock_llm.chat_stream = MagicMock(return_value=mock_stream)

        with patch("backend.app.agent.planner.LLMClient", return_value=mock_llm):
            resp = await async_client.post(
                "/api/chat",
                json={"message": "想去成都玩三天"},
                headers={"Authorization": auth_headers},
            )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/event-stream")

        events, full_text = await _collect_sse_events(resp)
        assert len(events) >= 2  # token + done
        assert "成都" in full_text
        assert events[-1]["type"] == "done"

    async def test_chat_existing_trip(self, async_client: AsyncClient, auth_headers: str):
        """传 trip_id → 继续已有行程的对话"""
        # 先创建一个行程，拿到 trip_id
        mock_chunks = ['{"destination": "北京"', '}\n']
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = mock_chunks
        mock_llm = MagicMock()
        mock_llm.chat_stream = MagicMock(return_value=mock_stream)

        with patch("backend.app.agent.planner.LLMClient", return_value=mock_llm):
            # 第一次请求创建新行程
            resp1 = await async_client.post(
                "/api/chat",
                json={"message": "想去北京玩三天"},
                headers={"Authorization": auth_headers},
            )
            events1, _ = await _collect_sse_events(resp1)
            assert events1[-1]["type"] == "done"

        # 从第一条事件里拿不到 trip_id，用 trips 列表接口获取
        list_resp = await async_client.get("/api/trips", headers={"Authorization": auth_headers})
        trips = list_resp.json()["trips"]
        assert len(trips) >= 1
        trip_id = trips[0]["id"]

        # 第二次请求，传 trip_id 继续对话
        mock_chunks2 = ['{"destination": "北京", "duration": 4', '}\n']
        mock_stream2 = AsyncMock()
        mock_stream2.__aiter__.return_value = mock_chunks2
        mock_llm2 = MagicMock()
        mock_llm2.chat_stream = MagicMock(return_value=mock_stream2)

        with patch("backend.app.agent.planner.LLMClient", return_value=mock_llm2):
            resp2 = await async_client.post(
                "/api/chat",
                json={"message": "把第二个景点改一下", "trip_id": trip_id},
                headers={"Authorization": auth_headers},
            )
            assert resp2.status_code == 200, resp.text

            events2, full_text2 = await _collect_sse_events(resp2)
            assert len(events2) >= 2
            assert events2[-1]["type"] == "done"

    async def test_chat_nonexistent_trip(self, async_client: AsyncClient, auth_headers: str):
        """传不存在的 trip_id → 404"""
        resp = await async_client.post(
            "/api/chat",
            json={"message": "继续行程", "trip_id": 99999},
            headers={"Authorization": auth_headers},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "行程不存在"

    async def test_chat_empty_message(self, async_client: AsyncClient, auth_headers: str):
        """空消息 → 422 校验错误"""
        resp = await async_client.post(
            "/api/chat",
            json={"message": ""},
            headers={"Authorization": auth_headers},
        )
        assert resp.status_code == 422

    async def test_chat_without_auth(self, async_client: AsyncClient):
        """未认证 → 422（Header missing）"""
        resp = await async_client.post(
            "/api/chat",
            json={"message": "想去玩"},
        )
        assert resp.status_code == 422

    async def test_chat_agent_error_yields_error_event(
        self, async_client: AsyncClient, auth_headers: str
    ):
        """Agent 内部抛异常 → SSE 流里出现 error 事件而不是 500"""
        mock_llm = MagicMock()
        mock_llm.chat_stream = MagicMock(side_effect=RuntimeError("LLM 调用失败"))

        with patch("backend.app.agent.planner.LLMClient", return_value=mock_llm):
            resp = await async_client.post(
                "/api/chat",
                json={"message": "想去成都玩三天"},
                headers={"Authorization": auth_headers},
            )

        events, _ = await _collect_sse_events(resp)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM 调用失败" in error_events[0]["detail"]

    async def test_chat_message_too_long(self, async_client: AsyncClient, auth_headers: str):
        """超长消息 → 422"""
        resp = await async_client.post(
            "/api/chat",
            json={"message": "x" * 2001},
            headers={"Authorization": auth_headers},
        )
        assert resp.status_code == 422


class TestChatCrossUser:
    """跨用户权限隔离"""

    async def test_cannot_access_other_user_trip(
        self, async_client: AsyncClient, auth_headers: str, auth_headers_alt: str
    ):
        """用户 B 不能访问用户 A 的行程"""
        # 用户 A 创建一个行程
        mock_chunks = ['{"destination": "杭州"', '}\n']
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = mock_chunks
        mock_llm = MagicMock()
        mock_llm.chat_stream = MagicMock(return_value=mock_stream)

        with patch("backend.app.agent.planner.LLMClient", return_value=mock_llm):
            resp = await async_client.post(
                "/api/chat",
                json={"message": "想去杭州玩"},
                headers={"Authorization": auth_headers},
            )
            await _collect_sse_events(resp)

        # 拿到用户 A 的 trip_id
        list_resp = await async_client.get("/api/trips", headers={"Authorization": auth_headers})
        trips = list_resp.json()["trips"]
        assert len(trips) >= 1
        trip_a_id = trips[0]["id"]

        # 用户 B 尝试续聊同一个 trip → 403（因为 A 的 trip 不属于 B）
        resp_b = await async_client.post(
            "/api/chat",
            json={"message": "我要看这个行程", "trip_id": trip_a_id},
            headers={"Authorization": auth_headers_alt},
        )
        assert resp_b.status_code == 403
