from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    prompt: str = Field(..., description="The complex prompt to be broken down into steps")
    file_ids: list[str] = Field(default_factory=list, description="IDs of files to attach to this task")
