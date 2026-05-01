"""Typed dataclasses for llimit task and file API JSON payloads."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


@dataclass
class FileMetadata:
    """File metadata as returned by upload, register-url, and list endpoints."""

    id: str
    filename: str
    description: str | None
    content_type: str
    size_bytes: int | None
    url: str | None
    created_at: datetime

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FileMetadata:
        return cls(
            id=data["id"],
            filename=data["filename"],
            description=data.get("description"),
            content_type=data["content_type"],
            size_bytes=data.get("size_bytes"),
            url=data.get("url"),
            created_at=_parse_dt(data["created_at"]) or datetime.min,
        )


@dataclass
class Task:
    """Task state from GET /task/{id} or POST /task."""

    id: str
    prompt: str
    title: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None
    steps_generated: bool
    output: str | None
    total_pre_request_estimated_cost_usd: float
    total_post_request_estimated_cost_usd: float
    total_or_cost_usd: float
    total_planning_or_cost_usd: float

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            prompt=data["prompt"],
            title=data.get("title"),
            status=data["status"],
            created_at=_parse_dt(data["created_at"]) or datetime.min,
            completed_at=_parse_dt(data.get("completed_at")),
            steps_generated=data.get("steps_generated", False),
            output=data.get("output"),
            total_pre_request_estimated_cost_usd=float(data.get("total_pre_request_estimated_cost_usd", 0.0)),
            total_post_request_estimated_cost_usd=float(data.get("total_post_request_estimated_cost_usd", 0.0)),
            total_or_cost_usd=float(data.get("total_or_cost_usd", 0.0)),
            total_planning_or_cost_usd=float(data.get("total_planning_or_cost_usd", 0.0)),
        )


@dataclass
class TaskStep:
    """A single task step from GET /task/{id}/steps."""

    id: str
    task_id: str
    step_number: int
    prompt: str
    status: str
    step_type: str
    complexity: str | None
    required_capabilities: list[str]
    model_name: str | None
    predicted_score: float | None
    predicted_length: float | None
    response_content: str | None
    output: str | None
    failure_reason: str | None
    is_planned: bool | None
    required_file_ids: list[str] | None
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TaskStep:
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            step_number=int(data["step_number"]),
            prompt=data["prompt"],
            status=data["status"],
            step_type=data["step_type"],
            complexity=data.get("complexity"),
            required_capabilities=list(data.get("required_capabilities") or []),
            model_name=data.get("model_name"),
            predicted_score=data.get("predicted_score"),
            predicted_length=data.get("predicted_length"),
            response_content=data.get("response_content"),
            output=data.get("output"),
            failure_reason=data.get("failure_reason"),
            is_planned=data.get("is_planned"),
            required_file_ids=data.get("required_file_ids"),
            started_at=_parse_dt(data.get("started_at")),
            completed_at=_parse_dt(data.get("completed_at")),
        )


@dataclass
class TaskList:
    """Response from GET /task."""

    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TaskList:
        tasks_raw = data.get("tasks") or []
        return cls(tasks=[Task.from_json(t) for t in tasks_raw])


@dataclass
class TaskStepList:
    """Response from GET /task/{id}/steps."""

    task_id: str
    steps: list[TaskStep] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TaskStepList:
        steps_raw = data.get("steps") or []
        return cls(
            task_id=data["task_id"],
            steps=[TaskStep.from_json(s) for s in steps_raw],
        )


@dataclass
class FileList:
    """Response from GET /files."""

    files: list[FileMetadata] = field(default_factory=list)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FileList:
        files_raw = data.get("files") or []
        return cls(files=[FileMetadata.from_json(f) for f in files_raw])


@dataclass
class TaskResult:
    """Terminal task state produced by wait-style polling."""

    task_id: str
    status: str
    output: str | None
    total_pre_request_estimated_cost_usd: float
    total_post_request_estimated_cost_usd: float
    total_or_cost_usd: float
    total_planning_or_cost_usd: float

    @classmethod
    def from_task(cls, task: Task) -> TaskResult:
        return cls(
            task_id=task.id,
            status=task.status,
            output=task.output,
            total_pre_request_estimated_cost_usd=task.total_pre_request_estimated_cost_usd,
            total_post_request_estimated_cost_usd=task.total_post_request_estimated_cost_usd,
            total_or_cost_usd=task.total_or_cost_usd,
            total_planning_or_cost_usd=task.total_planning_or_cost_usd,
        )


@dataclass
class WorkQueueItemInfo:
    """A single item in the work queue from GET /task/queue."""

    task_id: str
    step_id: str | None
    step_number: int | None
    item_type: str
    enqueue_time: datetime | None
    start_time: datetime | None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> WorkQueueItemInfo:
        return cls(
            task_id=data["task_id"],
            step_id=data.get("step_id"),
            step_number=data.get("step_number"),
            item_type=data["item_type"],
            enqueue_time=_parse_dt(data.get("enqueue_time")),
            start_time=_parse_dt(data.get("start_time")),
        )


@dataclass
class StoppedTaskInfo:
    """A task that is in an active state but has no queue items."""

    task_id: str
    title: str | None
    status: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> StoppedTaskInfo:
        return cls(
            task_id=data["task_id"],
            title=data.get("title"),
            status=data["status"],
        )


@dataclass
class WorkQueueState:
    """Response from GET /task/queue."""

    currently_processing: WorkQueueItemInfo | None
    pending: list[WorkQueueItemInfo]
    stopped_tasks: list[StoppedTaskInfo]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> WorkQueueState:
        raw_current = data.get("currently_processing")
        return cls(
            currently_processing=WorkQueueItemInfo.from_json(raw_current) if raw_current else None,
            pending=[WorkQueueItemInfo.from_json(i) for i in data.get("pending", [])],
            stopped_tasks=[StoppedTaskInfo.from_json(t) for t in data.get("stopped_tasks", [])],
        )
