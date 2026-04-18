from datetime import datetime
from pydantic import BaseModel, Field

from app.models.task.enums import TaskStatus, StepStatus, StepType, WorkItemType


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
    total_pre_request_estimated_cost_usd: float = Field(description="Pre-request estimated cost of step-execution calls (estimated input + predicted output tokens)")
    total_post_request_estimated_cost_usd: float = Field(description="Post-request estimated cost of step-execution calls (estimated input + real output tokens)")
    total_or_cost_usd: float = Field(description="OpenRouter-reported cost of step-execution calls")
    total_planning_or_cost_usd: float = Field(description="OpenRouter-reported cost of planning calls (decomposition and reevaluation)")


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
    predicted_score: float | None = Field(None, description="Predicted quality score for the selected model (not applicable for reevaluation steps)")
    predicted_length: float | None = Field(None, description="Predicted response length in tokens (not applicable for reevaluation steps)")
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


class WorkQueueItemInfo(BaseModel):
    task_id: str
    step_id: str | None
    step_number: int | None
    item_type: WorkItemType
    enqueue_time: datetime | None
    start_time: datetime | None


class StoppedTaskInfo(BaseModel):
    task_id: str
    title: str | None
    status: TaskStatus


class WorkQueueStateResponse(BaseModel):
    currently_processing: WorkQueueItemInfo | None
    pending: list[WorkQueueItemInfo]
    stopped_tasks: list[StoppedTaskInfo]

