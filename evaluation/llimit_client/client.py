"""Simple async client for interacting with the llimit task API."""
import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx

from evaluation.llimit_client.models import TaskResult, UploadedFile


_EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mpeg": "audio/mpeg",
    ".mp4": "video/mp4",
    ".mov": "video/mov",
    ".webm": "video/webm",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".xml": "text/xml",
    ".py": "text/x-python",
    ".json": "application/json",
    ".jsonld": "application/json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@dataclass
class LlimitConfig:
    """Configuration for connecting to a llimit API instance."""

    base_url: str
    api_key: str
    openrouter_api_key: str
    request_timeout: float = 30.0


class LlimitClient:
    """Async HTTP client wrapping the llimit task and file APIs."""

    def __init__(self, config: LlimitConfig) -> None:
        self._config = config
        self._base_headers = {
            "X-API-Key": config.api_key,
            "X-OpenRouter-API-Key": config.openrouter_api_key,
        }

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    async def upload_file(self, file_path: str | Path) -> UploadedFile:
        """Upload a local file and return its metadata."""
        path = Path(file_path)
        content_type = _EXTENSION_CONTENT_TYPES.get(
            path.suffix.lower(), "application/octet-stream"
        )

        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            with path.open("rb") as fh:
                response = await client.post(
                    f"{self._config.base_url}/files",
                    headers=self._base_headers,
                    files={"file": (path.name, fh, content_type)},
                    data={"content_type": content_type},
                )
        response.raise_for_status()
        data = response.json()
        return UploadedFile(file_id=data["id"], filename=data["filename"])

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    async def create_task(self, prompt: str, file_ids: list[str] | None = None) -> str:
        """Submit a new task and return its task ID."""
        body = {"prompt": prompt, "file_ids": file_ids or []}
        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            response = await client.post(
                f"{self._config.base_url}/task",
                headers={**self._base_headers, "Content-Type": "application/json"},
                json=body,
            )
        response.raise_for_status()
        return response.json()["id"]

    async def get_task(self, task_id: str) -> dict:
        """Fetch the current state of a task."""
        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            response = await client.get(
                f"{self._config.base_url}/task/{task_id}",
                headers=self._base_headers,
            )
        response.raise_for_status()
        return response.json()

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = 600.0,
        initial_interval: float = 2.0,
        max_interval: float = 30.0,
        backoff_factor: float = 1.5,
    ) -> TaskResult:
        """Poll a task until it reaches a terminal state or the timeout expires."""
        _TERMINAL = {"completed", "failed"}

        interval = initial_interval
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            data = await self.get_task(task_id)
            status: str = data["status"]

            if status in _TERMINAL:
                return TaskResult(
                    task_id=task_id,
                    status=status,
                    output=data.get("output"),
                    total_estimated_cost_usd=data.get("total_estimated_cost_usd", 0.0),
                    total_or_cost_usd=data.get("total_or_cost_usd", 0.0),
                )

            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(
                    f"Task {task_id} did not complete within {timeout:.0f}s "
                    f"(last status: {status})"
                )

            await asyncio.sleep(min(interval, remaining))
            interval = min(interval * backoff_factor, max_interval)
