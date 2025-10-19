from typing import Annotated

from fastapi import Depends, Request

from app.core.context import RequestContext
from app.db.chat_repo import ChatRepo
from app.db.database import Database
from app.db.user_repo import UserRepo
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.completion_stream_service import CompletionStreamService
from app.services.llm_service_base import LlmService
from app.services.llm_service import OpenRouterLlmService
from app.services.sse_service import SseService

# Singleton instances
_database_instance = Database()
_user_repo_instance = UserRepo(_database_instance)
_chat_repo_instance = ChatRepo(_database_instance)
_llm_service_instance = OpenRouterLlmService()
_auth_service_instance = AuthService(_user_repo_instance)
_sse_service_instance = SseService()


def get_database() -> Database:
    """Get the singleton Database instance"""
    return _database_instance


def get_user_repo() -> UserRepo:
    """Get the singleton UserRepo instance"""
    return _user_repo_instance


def get_chat_repo() -> ChatRepo:
    """Get the singleton ChatRepo instance"""
    return _chat_repo_instance



def get_llm_service() -> LlmService:
    """Get the singleton LlmService instance"""
    return _llm_service_instance


def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance"""
    return _auth_service_instance


def get_sse_service() -> SseService:
    """Get the singleton SseService instance"""
    return _sse_service_instance


def get_auth_context(require_openrouter_key: bool = True):
    """
    Authenticate request and return context.
    Requires X-API-Key header and optionally X-OpenRouter-API-Key header.
    """
    
    def _get_auth_context_inner(
        request: Request, 
        auth_service: Annotated[AuthService, Depends(get_auth_service)],
    ) -> RequestContext:
        return auth_service.authenticate(request, require_openrouter_key=require_openrouter_key)
    
    return _get_auth_context_inner


def get_chat_service(
    llm_service: Annotated[LlmService, Depends(get_llm_service)],
    chat_repo: Annotated[ChatRepo, Depends(get_chat_repo)],
    sse_service: Annotated[SseService, Depends(get_sse_service)],
) -> ChatService:
    """Get ChatService instance"""
    return ChatService(llm_service=llm_service, chat_repo=chat_repo, sse_service=sse_service)


def get_completion_stream_service(
    llm_service: Annotated[LlmService, Depends(get_llm_service)],
) -> CompletionStreamService:
    """Get CompletionStreamService instance"""
    return CompletionStreamService(llm_service=llm_service)


# Type annotations for dependencies
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
CompletionStreamServiceDep = Annotated[CompletionStreamService, Depends(get_completion_stream_service)]
LLMServiceDep = Annotated[LlmService, Depends(get_llm_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SseServiceDep = Annotated[SseService, Depends(get_sse_service)]


def AuthContextDep(require_openrouter_key: bool = True):
    return Annotated[RequestContext, Depends(get_auth_context(require_openrouter_key))]
