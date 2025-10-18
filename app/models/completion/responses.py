from pydantic import BaseModel


class CompletionResponse(BaseModel):
    role: str
    content: str
    additional_data: dict[str, str]

