"""
ConversationManager: 会话状态机、历史消息管理

管理一次行程规划对话的完整生命周期——创建会话、追踪状态、维护消息历史、控制上下文窗口大小。
"""
from enum import StrEnum
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.crud.trip import create_trip
from backend.app.crud.message import save_message
from backend.app.crud.message import get_all_trip_messages


class ConversationState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    CONFIRMING = "confirming"
    DONE = "done"





class ConversationManager:
    """会话状态机、上下文管理"""
    def __init__(self, db : AsyncSession, trip_id : int, user_id : int):
        self.db = db
        self.trip_id = trip_id
        self.user_id = user_id
        self.state: ConversationState = ConversationState.IDLE
        self.history_cache : list[dict] = [] # 历史对话的缓存



    async def create_conversation(self, title : str):
        """创建新会话，关联到某个 Trip"""
        trip = await create_trip(db=self.db, user_id=self.user_id, title=title ,status=self.state)
        self.trip_id = trip.id
        return trip

    async def add_message(self, role: str, content: str):
        """追加一条消息到会话历史"""
        message = await save_message(self.db, self.trip_id, role, content)
        self.history_cache.append({"role": role, "content": content})
        return message

    async def get_context(self, max_tokens: int):
        """返回拼接后的上下文字符串，自动裁剪到 max_tokens 以内"""
        db_messages = await get_all_trip_messages(self.db, self.trip_id)
        all_history = [
            {"role": db_message.role, "content": db_message.content}
            for db_message in db_messages
        ]
        result = []
        current_token = 0
        for msg in reversed(all_history):
            message_tokens = len(msg["content"]) // 2
            if current_token + message_tokens > max_tokens:
                break
            result.insert(0, msg)
            current_token += message_tokens
        self.history_cache = result
        return result


    def get_state(self) -> str:
        """返回当前会话状态（idle / planning / confirming / done）"""
        return self.state.value
