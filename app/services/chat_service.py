from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from dataclasses import dataclass

from app.models.chat.requests import (
    CreateChatThreadRequest,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.models.chat.models import (
    ChatThread,
    ChatMessage,
)
from app.services.llm_service import FunctionArgument, LlmFunctionSpec, LlmMessage, LlmService


# TODO: use db instead of static variable
_static_threads: dict[str, "ChatService.ThreadAndMessages"] = {}

class ChatService:

    @dataclass
    class ThreadAndMessages:
        thread: ChatThread
        messages: list[ChatMessage]

    def __init__(self, llm_service: LlmService) -> None:
        self._threads: dict[str, ChatService.ThreadAndMessages] = _static_threads
        self._llm_service = llm_service
    
    async def create_thread(self, request: CreateChatThreadRequest) -> ChatThread:
        thread_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        thread = ChatThread(
            id=thread_id,
            title=request.title,
            description=request.description,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            model_name=request.model_name,
            message_count=0,
        )
        
        self._threads[thread_id] = ChatService.ThreadAndMessages(
            thread=thread,
            messages=[],
        )
        
        return thread
    
    async def get_thread(self, thread_id: str) -> ChatThread | None:
        return self._threads.get(thread_id).thread
    
    async def list_threads(self) -> list[ChatThread]:
        return [t.thread for t in sorted(
            self._threads.values(),
            key=lambda t: t.thread.updated_at,
            reverse=True,
        )]
    
    async def update_thread(self, thread_id: str, request: UpdateThreadRequest) -> ChatThread | None:
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        
        if request.title is not None:
            thread.thread.title = request.title
        if request.description is not None:
            thread.thread.description = request.description
        
        thread.thread.updated_at = datetime.now(timezone.utc)
        
        return thread.thread
    
    async def send_message(self, thread_id: str, request: SendMessageRequest, api_key: str | None = None) -> str | None:
        if (thread := self._threads.get(thread_id)) is None:
            return None
        
        user_message_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        user_message = ChatMessage(
            id=user_message_id,
            role="user",
            content=request.content,
            created_at=now,
        )

        thread.messages.append(user_message)

        _ = self._llm_service.get_completion(
            model=thread.thread.model_name,
            messages=[
                LlmMessage(
                    role="system", 
                    content="You are a helpful assistant that can help with tasks and questions."
                    + " Current conversation title: {thread.thread.title}. Current conversation description: {thread.thread.description}."
                    + " You can use a tool to set the title and/or description of the conversation."
                    + " If they are not set, please set them to something relevant to the conversation."
                    + " Otherwise, you can update them if necessary, but if they still fit the conversation, do not change them."),
                *[LlmMessage(role=msg.role, content=msg.content) for msg in thread.messages],
            ],
            tools=[
                LlmFunctionSpec(
                    name="set_metaddata",
                    description="Set title and/or description of the conversation",
                    parameters=[
                        FunctionArgument(
                            name="title",
                            type="string",
                            description="The title of the conversation",
                            required=False,
                        ),
                        FunctionArgument(
                            name="description",
                            type="string",
                            description="The description of the conversation",
                            required=False,
                        ),
                    ],
                    execute=lambda args: self._set_metadata_by_llm(thread, args),
                ),
            ],
            temperature=0.7,
            max_tokens=None,
            api_key=api_key,
        )


        return user_message_id

    def _set_metadata_by_llm(self, thread: ThreadAndMessages, args: dict[str, Any]) -> None:
        _ = self.update_thread(thread.thread.id, UpdateThreadRequest(title=args.get("title"), description=args.get("description")))
    
    async def get_messages(self, thread_id: str) -> list[ChatMessage] | None:
        if (thread := self._threads.get(thread_id)) is None:
            return None
        
        return thread.messages
