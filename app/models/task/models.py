from datetime import datetime
from dataclasses import dataclass

from app.models.task.enums import TaskStatus, StepStatus
from app.models.task.responses import TaskResponse, TaskStepResponse


@dataclass
class Task:
    id: str
    user_id: str
    prompt: str
    title: str | None
    status: TaskStatus
    created_at: datetime
    completed_at: datetime | None
    steps_generated: bool

    def to_response(self) -> TaskResponse:
        return TaskResponse(
            id=self.id,
            prompt=self.prompt,
            title=self.title,
            status=self.status,
            created_at=self.created_at,
            completed_at=self.completed_at,
            steps_generated=self.steps_generated,
        )


@dataclass
class TaskStep:
    id: str
    task_id: str
    step_number: int
    prompt: str
    status: StepStatus
    model_name: str | None
    response_content: str | None
    started_at: datetime | None
    completed_at: datetime | None
    # Additional data for step dependencies and context
    depends_on_steps: list[int]  # List of step numbers this step depends on
    # TODO: Is that needed? Maybe we should have some other way to handle dependencies?
    additional_context: dict[str, str] | None  # Extra context for this step

    def to_response(self) -> TaskStepResponse:
        return TaskStepResponse(
            id=self.id,
            task_id=self.task_id,
            step_number=self.step_number,
            prompt=self.prompt,
            status=self.status,
            model_name=self.model_name,
            response_content=self.response_content,
            started_at=self.started_at,
            completed_at=self.completed_at,
            depends_on_steps=self.depends_on_steps,
            additional_context=self.additional_context,
        )

