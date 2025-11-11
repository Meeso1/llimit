from datetime import datetime
from dataclasses import dataclass
from abc import ABC

from app.models.task.enums import TaskStatus, StepStatus, StepType, ComplexityLevel, ModelCapability
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
    output: str | None

    def to_response(self) -> TaskResponse:
        return TaskResponse(
            id=self.id,
            prompt=self.prompt,
            title=self.title,
            status=self.status,
            created_at=self.created_at,
            completed_at=self.completed_at,
            steps_generated=self.steps_generated,
            output=self.output,
        )


@dataclass
class TaskStep(ABC):
    """Base class for all task step types"""
    id: str
    task_id: str
    step_number: int
    prompt: str
    status: StepStatus
    step_type: StepType
    response_content: str | None
    started_at: datetime | None
    completed_at: datetime | None

    def to_response(self) -> TaskStepResponse:
        """Convert to response DTO - implemented differently for each type"""
        raise NotImplementedError


@dataclass
class NormalTaskStep(TaskStep):
    """Normal execution step with model selection"""
    complexity: ComplexityLevel
    required_capabilities: list[ModelCapability]
    model_name: str | None
    output: str | None

    def to_response(self) -> TaskStepResponse:
        return TaskStepResponse(
            id=self.id,
            task_id=self.task_id,
            step_number=self.step_number,
            prompt=self.prompt,
            status=self.status,
            step_type=self.step_type,
            complexity=self.complexity,
            required_capabilities=self.required_capabilities,
            model_name=self.model_name,
            response_content=self.response_content,
            output=self.output,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


@dataclass
class ReevaluateTaskStep(TaskStep):
    """Reevaluation step that generates new steps"""

    def to_response(self) -> TaskStepResponse:
        return TaskStepResponse(
            id=self.id,
            task_id=self.task_id,
            step_number=self.step_number,
            prompt=self.prompt,
            status=self.status,
            step_type=self.step_type,
            complexity=None,
            required_capabilities=[],
            model_name=None,
            response_content=self.response_content,
            output=None,
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


@dataclass
class TaskStepDefinition(ABC):
    """Base class for step definitions"""
    prompt: str
    step_type: StepType


@dataclass
class NormalTaskStepDefinition(TaskStepDefinition):
    """Definition for normal execution steps"""
    complexity: ComplexityLevel
    required_capabilities: list[ModelCapability]


@dataclass
class ReevaluateTaskStepDefinition(TaskStepDefinition):
    """Definition for reevaluation steps"""
    pass


@dataclass
class TaskDecompositionResult:
    title: str
    steps: list[TaskStepDefinition]
