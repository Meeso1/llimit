from datetime import datetime
from dataclasses import dataclass

from app.models.chat.responses import ChatMessageResponse, ChatThreadResponse


@dataclass
class ChatMessage:
    id: str
    role: str
    content: str
    created_at: datetime

    def to_response(self) -> ChatMessageResponse:
        return ChatMessageResponse(
            id=self.id,
            role=self.role,
            content=self.content,
            created_at=self.created_at,
        )


@dataclass
class ChatThread:
    id: str
    user_id: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    model_name: str
    message_count: int

    def to_response(self) -> ChatThreadResponse:
        return ChatThreadResponse(
            id=self.id,
            title=self.title,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
            model_name=self.model_name,
            message_count=self.message_count,
        )


@dataclass
class ThreadWithMessages:
    thread: ChatThread
    messages: list[ChatMessage]
