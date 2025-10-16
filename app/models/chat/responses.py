from datetime import datetime
from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    additional_data: dict[str, str]


class ChatThreadResponse(BaseModel):
    id: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    model_name: str
    message_count: int


class ChatThreadListResponse(BaseModel):
    threads: list[ChatThreadResponse]
