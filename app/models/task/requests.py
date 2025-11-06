from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    prompt: str = Field(..., description="The complex prompt to be broken down into steps")
