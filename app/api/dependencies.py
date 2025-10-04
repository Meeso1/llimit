from typing import Annotated

from fastapi import Depends

from app.core.context import RequestContext
from app.middleware.auth import create_request_context
from app.services.chat_service import ChatService
from app.services.llm_service import LlmService
from app.services.user_service import UserService


# Singleton instances
_llm_service_instance = LlmService()
_user_service_instance = UserService()


def get_user_service() -> UserService:
    """Get the singleton UserService instance"""
    return _user_service_instance


def get_llm_service() -> LlmService:
    """Get the singleton LlmService instance"""
    return _llm_service_instance


def get_chat_service(
    llm_service: Annotated[LlmService, Depends(get_llm_service)]
) -> ChatService:
    """
    Get ChatService instance.
    Note: This creates a new instance per request, but services themselves are stateless.
    The actual state (threads) would be in a database in production.
    """
    return ChatService(llm_service=llm_service)


def get_request_context(
    user_service: Annotated[UserService, Depends(get_user_service)],
    api_key: str | None = None,
    openrouter_api_key: str | None = None,
) -> RequestContext:
    """
    Get request context with user ID and OpenRouter API key.
    This is a wrapper that ensures user_service is properly injected.
    """
    # Import here to avoid circular dependency
    from fastapi import Security
    from app.middleware.auth import api_key_header, openrouter_api_key_header
    
    # This will be called by FastAPI's dependency injection
    # The actual implementation is in create_request_context
    raise NotImplementedError("This should not be called directly")


# Type annotations for dependencies
RequestContextDep = Annotated[RequestContext, Depends(create_request_context)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
LLMServiceDep = Annotated[LlmService, Depends(get_llm_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
