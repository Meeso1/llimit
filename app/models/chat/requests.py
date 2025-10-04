from pydantic import BaseModel, Field


class CreateChatThreadRequest(BaseModel):
    title: str | None = Field(None, description="Optional initial title")
    description: str | None = Field(None, description="Optional initial description")
    model_name: str = Field(..., description="Model name")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Message content")


class UpdateThreadRequest(BaseModel):
    title: str | None = None
    description: str | None = None

