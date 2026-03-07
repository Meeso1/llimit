"""API response DTOs for the llimit client."""
from dataclasses import dataclass


@dataclass
class TaskResult:
    """Result of a completed (or failed) llimit task."""

    task_id: str
    status: str
    output: str | None
    total_cost_usd: float


@dataclass
class UploadedFile:
    """Metadata returned after uploading a file."""

    file_id: str
    filename: str
