from datetime import datetime, timezone
from uuid import uuid4

from app.models.chat.requests import (
    CreateChatThreadRequest,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.models.chat.responses import (
    ChatMessage,
    ChatThreadResponse,
    SendMessageResponse,
)


class ChatService:
    def __init__(self) -> None:
        self._threads: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}
    
    async def create_thread(self, request: CreateChatThreadRequest) -> ChatThreadResponse:
        thread_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        thread = {
            "id": thread_id,
            "title": request.title or "New Conversation",
            "description": None,
            "created_at": now,
            "updated_at": now,
            "archived": False,
            "metadata": request.metadata,
        }
        
        self._threads[thread_id] = thread
        self._messages[thread_id] = []
        
        return ChatThreadResponse(
            id=thread["id"],
            title=thread["title"],
            description=thread["description"],
            created_at=thread["created_at"],
            updated_at=thread["updated_at"],
            message_count=0,
            archived=thread["archived"],
            metadata=thread["metadata"],
        )
    
    async def get_thread(self, thread_id: str) -> ChatThreadResponse | None:
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        
        message_count = len(self._messages.get(thread_id, []))
        
        return ChatThreadResponse(
            id=thread["id"],
            title=thread["title"],
            description=thread["description"],
            created_at=thread["created_at"],
            updated_at=thread["updated_at"],
            message_count=message_count,
            archived=thread["archived"],
            metadata=thread["metadata"],
        )
    
    async def list_threads(self, page: int = 1, page_size: int = 20) -> tuple[list[ChatThreadResponse], int]:
        all_threads = sorted(
            self._threads.values(),
            key=lambda t: t["updated_at"],
            reverse=True,
        )
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_threads = all_threads[start_idx:end_idx]
        
        responses = [
            ChatThreadResponse(
                id=thread["id"],
                title=thread["title"],
                description=thread["description"],
                created_at=thread["created_at"],
                updated_at=thread["updated_at"],
                message_count=len(self._messages.get(thread["id"], [])),
                archived=thread["archived"],
                metadata=thread["metadata"],
            )
            for thread in page_threads
        ]
        
        return responses, len(all_threads)
    
    async def update_thread(self, thread_id: str, request: UpdateThreadRequest) -> ChatThreadResponse | None:
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        
        if request.title is not None:
            thread["title"] = request.title
        if request.description is not None:
            thread["description"] = request.description
        if request.archived is not None:
            thread["archived"] = request.archived
        
        thread["updated_at"] = datetime.now(timezone.utc)
        
        return await self.get_thread(thread_id)
    
    async def send_message(self, thread_id: str, request: SendMessageRequest) -> SendMessageResponse | None:
        if thread_id not in self._threads:
            return None
        
        user_message_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        user_message = {
            "id": user_message_id,
            "role": "user",
            "content": request.content,
            "created_at": now,
        }
        self._messages[thread_id].append(user_message)
        
        assistant_message_id = str(uuid4())
        assistant_content = f"Mock response to: {request.content[:50]}..."
        
        assistant_message = {
            "id": assistant_message_id,
            "role": "assistant",
            "content": assistant_content,
            "created_at": datetime.now(timezone.utc),
        }
        self._messages[thread_id].append(assistant_message)
        
        self._threads[thread_id]["updated_at"] = datetime.now(timezone.utc)
        
        return SendMessageResponse(
            message_id=assistant_message_id,
            thread_id=thread_id,
            content=assistant_content,
            created_at=assistant_message["created_at"],
            finish_reason="stop",
        )
    
    async def get_messages(self, thread_id: str) -> list[ChatMessage] | None:
        if thread_id not in self._threads:
            return None
        
        messages = self._messages.get(thread_id, [])
        return [
            ChatMessage(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
            )
            for msg in messages
        ]
