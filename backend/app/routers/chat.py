"""
Chat 路由 — 核心对话端点

接收用户消息，走 Agent 流水线（意图分类 → LLM 生成 → JSON 解析 → 落库），
以 SSE（Server-Sent Events）流式返回给前端，实现打字机效果。
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.routers.dependencies import get_current_user
from backend.app.schemas.chat import ChatRequest
from backend.app.crud.trip import find_trip_by_id
from backend.app.agent.conversation import ConversationManager
from backend.app.agent.planner import TripPlannerAgent

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    核心对话端点，完整流程：

    1. 找到或创建行程（trip）
    2. 初始化 ConversationManager（会话状态机）
    3. 初始化 TripPlannerAgent（LLM 编排）
    4. 以 SSE 流式返回 Agent 的 yield 事件

    前端收到的每个事件格式：data: {"type": "token", "content": "..."}

    事件类型：
      {"type": "token",   "content": "..."}  — 逐字文本块（打字机效果）
      {"type": "done",    "data": {}}        — 流结束
      {"type": "error",   "detail": "..."}   — 异常信息（如有）
    """

    # ── 步骤 1：找到或创建行程 ──────────────────────────────────────────
    # 两种情况：
    #   A) 前端传了 trip_id → 用户继续之前的对话 → 从数据库找回行程
    #   B) 前端没传 trip_id → 用户第一次聊天 → 需要创建新行程
    #
    # 注意：Schema 里 trip_id 是 int | None，前端传值就是 int，不用转换

    if request.trip_id is not None:
        # 情况 A：已有行程，查数据库确认存在 + 归属校验
        trip = await find_trip_by_id(db, request.trip_id)
        if trip is None:
            raise HTTPException(status_code=404, detail="行程不存在")
        if trip.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问该行程")
        trip_id = trip.id  # 用数据库查出来的值，不信任前端
    else:
        # 情况 B：新行程，先用 0 占位
        # 等 ConversationManager.create_conversation() 执行后会自动更新
        trip_id = 0

    # ── 步骤 2：初始化 ConversationManager ─────────────────────────────
    # 这个对象贯穿整个请求生命周期，它负责：
    #   - 追踪会话状态机（IDLE → PLANNING → CONFIRMING → DONE）
    #   - 管理消息历史（内存缓存 history_cache + 数据库 Message 表）
    #   - 控制上下文窗口大小（按 max_tokens 裁剪）
    conversation_manager = ConversationManager(
        db=db,
        trip_id=trip_id,
        user_id=current_user.id,
    )

    # 如果前面 trip_id 是 0（新行程），现在才真正创建数据库记录
    if request.trip_id is None:
        # create_conversation 内部调用 crud.create_trip() 写入 trip 表
        # 然后把返回的 trip.id 赋值给 self.trip_id
        # 所以这行执行完，conversation_manager.trip_id 就不再是 0 了
        await conversation_manager.create_conversation(title="新行程")

    # ── 步骤 3：初始化 Agent ───────────────────────────────────────────
    agent = TripPlannerAgent()

    # ── 步骤 4：构造 SSE 生成器并返回流式响应 ──────────────────────────

    async def event_generator():
        """
        SSE 事件生成器。

        agent.handle_message() 是一个 async generator（内部用 yield 往外吐数据），
        这里用 async for 逐个消费，把每个事件对象序列化为 SSE 格式字符串：

            data: {"type": "token", "content": "成"}\n\n
            data: {"type": "token", "content": "都"}\n\n
            data: {"type": "done",  "data": {}}\n\n

        前端用 EventSource 或 fetch + ReadableStream 接收即可。
        """
        try:
            async for event in agent.handle_message(
                request.message,        # 用户输入的文本
                conversation_manager,   # 会话管理器（Agent 内部会调用 add_message / get_context）
            ):
                # SSE 协议格式：每行 "data: <json>\n\n" 表示一个事件
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            # Agent 内部如果抛了未捕获的异常，用 error 事件告知前端
            error_event = {"type": "error", "detail": str(exc)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",          # 禁止浏览器/CDN 缓存 SSE 流
            "Connection": "keep-alive",           # 保持长连接
            "X-Accel-Buffering": "no",            # 禁用 Nginx 代理缓冲（如果有的话）
        },
    )
