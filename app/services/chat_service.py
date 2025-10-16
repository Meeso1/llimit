import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.db.chat_repo import ChatRepo
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


class ChatService:
    def __init__(self, llm_service: LlmService, chat_repo: ChatRepo) -> None:
        self._llm_service = llm_service
        self._chat_repo = chat_repo
    
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
    
    async def send_message(self, thread_id: str, user_id: str, request: SendMessageRequest, api_key: str | None = None) -> str | None:
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
            )
        )
        
        return user_message_id
    
    async def _process_llm_response(
        self,
        thread_id: str,
        user_id: str,
        model_name: str,
        api_key: str | None,
    ) -> None:
        """Process LLM response in background and save to database"""
        try:
            # Get all messages for context
            messages = self._chat_repo.get_messages(thread_id, user_id)
            if messages is None:
                return
            
            # Get thread for metadata
            thread = self._chat_repo.get_thread_by_id_and_user(thread_id, user_id)
            if thread is None:
                return
            
            # Prepare messages for LLM
            llm_messages = [
                LlmMessage(
                    role="system",
                    content=(
                        f"You are a helpful assistant that can help with tasks and questions."
                        f" Current conversation title: {(thread.title or "[Not set]")}. Current conversation description: {(thread.description or "[Not set]")}."
                    )
                ),
                *[LlmMessage(role=msg.role, content=msg.content, additional_data=msg.additional_data) for msg in messages],
            ]
            
            response = await self._llm_service.get_completion(
                model=model_name,
                messages=llm_messages,
                additional_requested_data={
                    "title": "Title of the conversation. Only return this field if the title should be set/updated. If current title is appropriate, do not return this field.",
                    "description": "Description of the conversation. Only return this field if the description should be set/updated. If current description is appropriate, do not return this field.",
                },
                temperature=0.7,
                api_key=api_key,
            )
            
            # Save assistant response
            assistant_message_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            self._chat_repo.add_message(
                message_id=assistant_message_id,
                thread_id=thread_id,
                role="assistant",
                content=response.content,
                additional_data=response.additional_data,
                created_at=now,
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
    
    async def get_messages(self, thread_id: str, user_id: str) -> list[ChatMessage] | None:
        return self._chat_repo.get_messages(thread_id, user_id)
