from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.context import RequestContext

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
openrouter_api_key_header = APIKeyHeader(name="X-OpenRouter-API-Key", auto_error=False)


async def create_request_context(
    api_key: str | None = Security(api_key_header),
    openrouter_api_key: str | None = Security(openrouter_api_key_header),
) -> RequestContext:
    """
    Create request context by validating API keys and retrieving user information.
    This dependency provides request-scoped context to all services.
    """
    # Import here to avoid circular dependency
    from app.api.dependencies import get_user_service
    
    # Validate API key
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    
    # Validate OpenRouter API key
    if openrouter_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing OpenRouter API key",
        )
    
    # Get user by API key
    user_service = get_user_service()
    user = user_service.get_user_by_api_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Create and return request context
    return RequestContext(
        user_id=user.id,
        openrouter_api_key=openrouter_api_key,
    )
