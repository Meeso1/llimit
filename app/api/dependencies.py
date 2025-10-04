from typing import Annotated

from fastapi import Depends

from app.services.chat_service import ChatService
from app.services.llm_service import LlmService


_llm_service_instance = LlmService()
_chat_service_instance = ChatService(llm_service=_llm_service_instance)


def get_chat_service() -> ChatService:
    return _chat_service_instance


def get_llm_service() -> LlmService:
    return _llm_service_instance


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
LLMServiceDep = Annotated[LlmService, Depends(get_llm_service)]
