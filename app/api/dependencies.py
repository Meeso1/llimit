from typing import Annotated

from fastapi import Depends

from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService


_chat_service_instance = ChatService()
_memory_service_instance = MemoryService()
_llm_service_instance = LLMService()


def get_chat_service() -> ChatService:
    return _chat_service_instance


def get_memory_service() -> MemoryService:
    return _memory_service_instance


def get_llm_service() -> LLMService:
    return _llm_service_instance


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
