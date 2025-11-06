from datetime import datetime
from pydantic import BaseModel, Field

from app.models.task.enums import TaskStatus, StepStatus


class TaskResponse(BaseModel):
    id: str
    prompt: str
    title: str | None = Field(None, description="Generated title for the task")
    status: TaskStatus
    created_at: datetime
    completed_at: datetime | None
    steps_generated: bool = Field(
        description="Whether the task has been decomposed into steps yet"
    )


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class TaskStepResponse(BaseModel):
    id: str
    task_id: str
    step_number: int
    prompt: str
    status: StepStatus
    model_name: str | None = Field(None, description="The model selected for this step")
    response_content: str | None = Field(None, description="The LLM response for this step")
    started_at: datetime | None
    completed_at: datetime | None
    depends_on_steps: list[int] = Field(
        default_factory=list,
        description="Step numbers this step depends on"
    )
    additional_context: dict[str, str] | None = Field(
        None,
        description="Additional context provided for this step"
    )


class TaskStepListResponse(BaseModel):
    task_id: str
    steps: list[TaskStepResponse]

