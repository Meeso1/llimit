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
    total_estimated_cost_usd: float
    total_or_cost_usd: float

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
            total_estimated_cost_usd=float(data.get("total_estimated_cost_usd", 0.0)),
            total_or_cost_usd=float(data.get("total_or_cost_usd", 0.0)),
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
    total_estimated_cost_usd: float
    total_or_cost_usd: float

    @classmethod
    def from_task(cls, task: Task) -> TaskResult:
        return cls(
            task_id=task.id,
            status=task.status,
            output=task.output,
            total_estimated_cost_usd=task.total_estimated_cost_usd,
            total_or_cost_usd=task.total_or_cost_usd,
        )
