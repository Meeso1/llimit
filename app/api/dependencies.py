from typing import Annotated

from fastapi import Depends, Request

from app.core.context import RequestContext
from app.db.api_key_repo import ApiKeyRepo
from app.db.chat_repo import ChatRepo
from app.db.database import Database
from app.db.task_repo import TaskRepo
from app.db.user_repo import UserRepo
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.completion_stream_service import CompletionStreamService
from app.services.llm_service_base import LlmService
from app.services.llm_service import OpenRouterLlmService
from app.services.sse_service import SseService
from app.services.task_decomposition_service import TaskDecompositionService
from app.services.task_model_selection_service import TaskModelSelectionService
from app.services.task_service import TaskService

# Singleton instances
_database_instance = Database()
_user_repo_instance = UserRepo(_database_instance)
_api_key_repo_instance = ApiKeyRepo(_database_instance)
_chat_repo_instance = ChatRepo(_database_instance)
_task_repo_instance = TaskRepo(_database_instance)
_llm_service_instance = OpenRouterLlmService()
_sse_service_instance = SseService()
_api_key_service_instance = ApiKeyService(_api_key_repo_instance)
_auth_service_instance = AuthService(_api_key_service_instance)
_task_decomposition_service_instance = TaskDecompositionService(_llm_service_instance)
_task_model_selection_service_instance = TaskModelSelectionService()
_chat_service_instance = ChatService(
    llm_service=_llm_service_instance,
    chat_repo=_chat_repo_instance,
    sse_service=_sse_service_instance,
)
_completion_stream_service_instance = CompletionStreamService(llm_service=_llm_service_instance)
_task_service_instance = TaskService(
    task_repo=_task_repo_instance,
    llm_service=_llm_service_instance,
    sse_service=_sse_service_instance,
    decomposition_service=_task_decomposition_service_instance,
    model_selection_service=_task_model_selection_service_instance,
)


def get_database() -> Database:
    """Get the singleton Database instance"""
    return _database_instance


def get_user_repo() -> UserRepo:
    """Get the singleton UserRepo instance"""
    return _user_repo_instance


def get_chat_repo() -> ChatRepo:
    """Get the singleton ChatRepo instance"""
    return _chat_repo_instance


def get_api_key_repo() -> ApiKeyRepo:
    """Get the singleton ApiKeyRepo instance"""
    return _api_key_repo_instance

def get_task_repo() -> TaskRepo:
    """Get the singleton TaskRepo instance"""
    return _task_repo_instance


def get_api_key_service() -> ApiKeyService:
    """Get the singleton ApiKeyService instance"""
    return _api_key_service_instance


def get_llm_service() -> LlmService:
    """Get the singleton LlmService instance"""
    return _llm_service_instance


def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance"""
    return _auth_service_instance


def get_sse_service() -> SseService:
    """Get the singleton SseService instance"""
    return _sse_service_instance


def get_task_decomposition_service() -> TaskDecompositionService:
    """Get the singleton TaskDecompositionService instance"""
    return _task_decomposition_service_instance


def get_task_model_selection_service() -> TaskModelSelectionService:
    """Get the singleton TaskModelSelectionService instance"""
    return _task_model_selection_service_instance


def get_chat_service() -> ChatService:
    """Get the singleton ChatService instance"""
    return _chat_service_instance


def get_completion_stream_service() -> CompletionStreamService:
    """Get the singleton CompletionStreamService instance"""
    return _completion_stream_service_instance


def get_task_service() -> TaskService:
    """Get the singleton TaskService instance"""
    return _task_service_instance


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


# Type annotations for dependencies
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
CompletionStreamServiceDep = Annotated[CompletionStreamService, Depends(get_completion_stream_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
LLMServiceDep = Annotated[LlmService, Depends(get_llm_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SseServiceDep = Annotated[SseService, Depends(get_sse_service)]


def AuthContextDep(require_openrouter_key: bool = True):
    return Annotated[RequestContext, Depends(get_auth_context(require_openrouter_key))]
