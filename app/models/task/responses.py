from datetime import datetime
from pydantic import BaseModel, Field

from app.models.task.enums import TaskStatus, StepStatus, StepType


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
    output: str | None = Field(None, description="Output from the last step of the task")


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class TaskStepResponse(BaseModel):
    id: str
    task_id: str
    step_number: int
    prompt: str
    status: StepStatus
    step_type: StepType
    complexity: str | None = Field(None, description="Complexity level (not applicable for reevaluation steps)")
    required_capabilities: list[str] = Field(default_factory=list, description="Required capabilities (not applicable for reevaluation steps)")
    model_name: str | None = Field(None, description="The model selected for this step (not applicable for reevaluation steps)")
    response_content: str | None = Field(None, description="The LLM response for this step")
    output: str | None = Field(None, description="Concise output from the step")
    failure_reason: str | None = Field(None, description="Reason for step failure if the step could not be completed (only for normal steps)")
    is_planned: bool | None = Field(None, description="Whether this reevaluation was planned or triggered by a step failure (only for reevaluation steps)")
    required_file_ids: list[str] | None = Field(None, description="Files required for this step (not applicable for reevaluation steps)")
    started_at: datetime | None
    completed_at: datetime | None


class TaskStepListResponse(BaseModel):
    task_id: str
    steps: list[TaskStepResponse]

