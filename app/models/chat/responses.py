from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatThreadResponse(BaseModel):
    id: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int
    archived: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class ChatThreadListResponse(BaseModel):
    threads: list[ChatThreadResponse]
    total: int
    page: int
    page_size: int


class SendMessageResponse(BaseModel):
    message_id: str
    thread_id: str
    content: str
    created_at: datetime
    finish_reason: str | None = None

