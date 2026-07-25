"""
ChatRequest, ChatStreamChunk
"""


from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(...,min_length=1, max_length=2000, description="用户发送的信息")
    trip_id: int | None = Field(None, description="已有行程ID，不传则创建新行程")


# SSE 事件的 data 载荷
class TokenEvent(BaseModel):
    content: str

class PlanEvent(BaseModel):
    trip_id: str
    title: str
    plan_data: dict  # 对应 PlanData 结构

class ErrorEvent(BaseModel):
    detail: str

class DoneEvent(BaseModel):
    pass
