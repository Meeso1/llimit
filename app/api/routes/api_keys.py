from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import AuthContextDep, get_api_key_service
from app.services.api_key_service import ApiKeyService
from app.models.apikey.requests import CreateApiKeyRequest
from app.models.apikey.responses import (
    ApiKeyResponse,
    CreateApiKeyResponse,
    DeleteApiKeyResponse,
    ListApiKeysResponse,
)


router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
)


ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]


@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request_body: CreateApiKeyRequest,
    context: AuthContextDep(require_openrouter_key=False),
    api_key_service: ApiKeyServiceDep,
) -> CreateApiKeyResponse:
    """
    Create a new API key for the authenticated user.
    
    **Warning**: The API key is only shown once. Save it securely.
    """
    result = api_key_service.create_api_key(
        user_id=context.user_id,
        name=request_body.name,
    )
    
    return CreateApiKeyResponse(
        id=result.key_id,
        name=result.name,
        key=result.plaintext_key,
        created_at=result.created_at,
    )


@router.get("", response_model=ListApiKeysResponse)
async def list_api_keys(
    context: AuthContextDep(require_openrouter_key=False),
    api_key_service: ApiKeyServiceDep,
    include_deleted: bool = False,
) -> ListApiKeysResponse:
    """
    List all API keys for the authenticated user.
    
    Keys are sorted by creation time (newest first).
    By default, deleted keys are not shown.
    """
    api_keys = api_key_service.list_user_api_keys(context.user_id, include_deleted)
    
    return ListApiKeysResponse(
        keys=[
            ApiKeyResponse(
                id=key.id,
                name=key.name,
                created_at=key.created_at,
                deleted_at=key.deleted_at,
            )
            for key in api_keys
        ]
    )


@router.delete("/{key_id}", response_model=DeleteApiKeyResponse)
async def delete_api_key(
    key_id: str,
    context: AuthContextDep(require_openrouter_key=False),
    api_key_service: ApiKeyServiceDep,
) -> DeleteApiKeyResponse:
    """
    Delete (soft delete) an API key.
    
    Note: You cannot delete the API key that is currently being used for authentication.
    """
    # Prevent deleting the key being used for authentication
    if key_id == context.api_key_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot delete the API key currently being used for authentication",
        )
    
    # Get the API key to verify ownership
    api_key = api_key_service.get_api_key_by_id(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Verify the key belongs to the user
    if api_key.user_id != context.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this API key",
        )
    
    # Soft delete the key (only if not already deleted)
    if api_key.deleted_at is None:
        api_key_service.delete_api_key(key_id)
    
    return DeleteApiKeyResponse(
        id=key_id,
        message=f"API key '{api_key.name}' has been deleted",
    )

