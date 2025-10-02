from pydantic import BaseModel, Field


class CreateChatThreadRequest(BaseModel):
    title: str | None = Field(None, description="Optional initial title")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Message content")
    stream: bool = Field(False, description="Whether to stream the response")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int | None = Field(None, description="Maximum tokens to generate")


class UpdateThreadRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    archived: bool | None = None

