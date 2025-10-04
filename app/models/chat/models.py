from datetime import datetime
from dataclasses import dataclass


@dataclass
class ChatMessage:
    id: str
    role: str
    content: str
    created_at: datetime


@dataclass
class ChatThread:
    id: str
    title: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    model_name: str
    message_count: int


@dataclass
class ThreadWithMessages:
    thread: ChatThread
    messages: list[ChatMessage]
