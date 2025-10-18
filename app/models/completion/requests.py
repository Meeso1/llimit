from pydantic import BaseModel, Field


class LlmMessageRequest(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")
    additional_data: dict[str, str] = Field(default_factory=dict, description="Additional structured data")


class CompletionRequest(BaseModel):
    model: str = Field(..., description="Model identifier to use for completion")
    prompt: str = Field(..., min_length=1, description="User prompt to send to the model")
    messages: list[LlmMessageRequest] | None = Field(
        None, 
        description="Optional conversation history. The prompt will be appended as a user message."
    )
    additional_requested_data: dict[str, str] | None = Field(
        None, 
        description="Dictionary of additional data to request from the model. Keys are field names, values are descriptions."
    )
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")

