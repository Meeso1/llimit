import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.db.chat_repo import ChatRepo
from utils import not_none
from app.events.new_llm_message import new_llm_message
from app.events.new_llm_message_chunk import new_llm_message_chunk
from app.models.chat.requests import (
    CreateChatThreadRequest,
    SendMessageRequest,
    UpdateThreadRequest,
)
from app.models.chat.models import (
    ChatThread,
    ChatMessage,
)
from app.services.llm_service import LlmMessage, LlmService
from app.services.sse_service import SseService
from app.events.thread_created import thread_created
from prompts.chat_prompts import (
    CHAT_SYSTEM_MESSAGE_TEMPLATE,
    CHAT_TITLE_DESCRIPTION,
    CHAT_DESCRIPTION_DESCRIPTION,
)


class ChatService:
    def __init__(self, llm_service: LlmService, chat_repo: ChatRepo, sse_service: SseService) -> None:
        self._llm_service = llm_service
        self._chat_repo = chat_repo
        self._sse_service = sse_service
    
    async def create_thread(self, user_id: str, request: CreateChatThreadRequest) -> ChatThread:
        thread_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        thread = self._chat_repo.create_thread(
            thread_id=thread_id,
            user_id=user_id,
            title=request.title,
            description=request.description,
            model_name=request.model_name,
            created_at=now,
        )
        
        await self._sse_service.emit_event(
            user_id=user_id,
            event=thread_created(thread))
        
        return thread
    
    async def get_thread(self, thread_id: str, user_id: str) -> ChatThread | None:
        return self._chat_repo.get_thread_by_id_and_user(thread_id, user_id)
    
    async def list_threads(self, user_id: str) -> list[ChatThread]:
        return self._chat_repo.list_threads_by_user(user_id)
    
    async def update_thread(self, thread_id: str, user_id: str, request: UpdateThreadRequest) -> ChatThread | None:
        return self._chat_repo.update_thread(
            thread_id=thread_id,
            user_id=user_id,
            title=request.title,
            description=request.description,
        )
    
    async def send_message(
        self,
        thread_id: str,
        user_id: str,
        request: SendMessageRequest,
        api_key: str,
        stream: bool = False,
    ) -> str | None:
        # Verify thread exists and belongs to user
        thread = await self.get_thread(thread_id, user_id)
        if thread is None:
            return None
        
        # Create and save user message
        user_message_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        self._chat_repo.add_message(
            message_id=user_message_id,
            thread_id=thread_id,
            role="user",
            content=request.content,
            created_at=now,
        )
        
        # Start LLM processing in background (fire and forget)
        asyncio.create_task(
            self._process_llm_response(
                thread_id=thread_id,
                user_id=user_id,
                model_name=thread.model_name,
                api_key=api_key,
            ) \
            if not stream else \
            self._process_llm_response_streamed(
                thread_id=thread_id,
                user_id=user_id,
                model_name=thread.model_name,
                api_key=api_key,
            )
        )
        
        return user_message_id
    
    def _prepare_llm_messages(self, thread_id: str, user_id: str) -> list[LlmMessage]:
        messages = not_none(
            self._chat_repo.get_messages(thread_id, user_id),
            f"Messages for thread {thread_id} and user {user_id}"
        )
        
        # Get thread for metadata
        thread = not_none(
            self._chat_repo.get_thread_by_id_and_user(thread_id, user_id),
            f"Thread {thread_id} for user {user_id}"
        )
        
        return [
            LlmMessage(
                role="system",
                content=CHAT_SYSTEM_MESSAGE_TEMPLATE.format(
                    title=thread.title or "[Not set]",
                    description=thread.description or "[Not set]",
                ),
                additional_data={},
            ),
            *[LlmMessage(role=msg.role, content=msg.content, additional_data=msg.additional_data) for msg in messages],
        ]
    
    async def _process_llm_response(
        self,
        thread_id: str,
        user_id: str,
        model_name: str,
        api_key: str,
    ) -> None:
        try:
            response = await self._llm_service.get_completion(
                api_key=api_key,
                model=model_name,
                messages=self._prepare_llm_messages(thread_id, user_id),
                additional_requested_data={
                    "title": CHAT_TITLE_DESCRIPTION,
                    "description": CHAT_DESCRIPTION_DESCRIPTION,
                },
                temperature=0.7,
            )
            
            assistant_message = self._chat_repo.add_message(
                message_id=str(uuid4()),
                thread_id=thread_id,
                role="assistant",
                content=response.content,
                additional_data=response.additional_data,
                created_at=datetime.now(timezone.utc),
            )

            await self._sse_service.emit_event(
                user_id=user_id,
                event=new_llm_message(thread_id, assistant_message),
            )

            # Update thread metadata if needed
            new_title = response.additional_data.get("title")
            new_description = response.additional_data.get("description")

            if new_title is not None or new_description is not None:
                self._chat_repo.update_thread(
                    thread_id=thread_id,
                    user_id=user_id,
                    title=new_title,
                    description=new_description,
                )
        except Exception as e:
            # Log error but don't crash
            print(f"Error processing LLM response: {e}")
    
    async def _process_llm_response_streamed(
        self,
        thread_id: str,
        user_id: str,
        model_name: str,
        api_key: str,
    ) -> None:
        try:
            llm_messages = self._prepare_llm_messages(thread_id, user_id)
            response_chunks = await self._llm_service.get_completion_streamed(
                api_key=api_key,
                model=model_name,
                messages=llm_messages,
                additional_requested_data={
                    "title": CHAT_TITLE_DESCRIPTION,
                    "description": CHAT_DESCRIPTION_DESCRIPTION,
                },
                temperature=0.7,
            )
            
            assistant_message_id = str(uuid4())
            
            message_content = ""
            additional_data = {}
            async for chunk in response_chunks:
                if chunk.additional_data_key is not None:
                    if chunk.additional_data_key in additional_data:
                        additional_data[chunk.additional_data_key] += chunk.content
                    else:
                        additional_data[chunk.additional_data_key] = chunk.content
                else:
                    message_content += chunk.content

                await self._sse_service.emit_event(
                    user_id=user_id,
                    event=new_llm_message_chunk(thread_id, assistant_message_id, chunk),
                )
                
            assistant_message = self._chat_repo.add_message(
                message_id=assistant_message_id,
                thread_id=thread_id,
                role="assistant",
                content=message_content,
                additional_data=additional_data,
                created_at=datetime.now(timezone.utc),
            )
            
            await self._sse_service.emit_event(
                user_id=user_id,
                event=new_llm_message(thread_id, assistant_message),
            )

        except Exception as e:
            print(f"Error processing LLM response: {e}")
    
    
    async def get_messages(self, thread_id: str, user_id: str) -> list[ChatMessage] | None:
        return self._chat_repo.get_messages(thread_id, user_id)
