from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name for the API key")

