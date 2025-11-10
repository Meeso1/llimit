from datetime import datetime
from dataclasses import dataclass

from app.models.task.enums import TaskStatus, StepStatus, ComplexityLevel, ModelCapability
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
    complexity: ComplexityLevel
    required_capabilities: list[ModelCapability]
    model_name: str | None
    response_content: str | None
    output: str | None
    started_at: datetime | None
    completed_at: datetime | None

    def to_response(self) -> TaskStepResponse:
        return TaskStepResponse(
            id=self.id,
            task_id=self.task_id,
            step_number=self.step_number,
            prompt=self.prompt,
            status=self.status,
            complexity=self.complexity,
            required_capabilities=self.required_capabilities,
            model_name=self.model_name,
            response_content=self.response_content,
            output=self.output,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


@dataclass
class TaskStepDefinition:
    prompt: str
    complexity: ComplexityLevel
    required_capabilities: list[ModelCapability]


@dataclass
class TaskDecompositionResult:
    title: str
    steps: list[TaskStepDefinition]
