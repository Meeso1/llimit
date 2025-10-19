from datetime import datetime
from pydantic import BaseModel, Field


class ApiKeyResponse(BaseModel):
    """Response model for API key information (without the actual key)"""
    id: str = Field(..., description="Unique API key ID")
    name: str = Field(..., description="Name of the API key")
    created_at: datetime = Field(..., description="When the key was created")
    deleted_at: datetime | None = Field(None, description="When the key was deleted, if applicable")


class CreateApiKeyResponse(BaseModel):
    """Response model when creating a new API key (includes the plaintext key)"""
    id: str = Field(..., description="Unique API key ID")
    name: str = Field(..., description="Name of the API key")
    key: str = Field(..., description="The actual API key (only shown once)")
    created_at: datetime = Field(..., description="When the key was created")


class ListApiKeysResponse(BaseModel):
    """Response model for listing API keys"""
    keys: list[ApiKeyResponse] = Field(..., description="List of API keys")


class DeleteApiKeyResponse(BaseModel):
    """Response model after deleting an API key"""
    id: str = Field(..., description="ID of the deleted API key")
    message: str = Field(..., description="Confirmation message")

