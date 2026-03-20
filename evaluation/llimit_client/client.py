"""Async HTTP client for the llimit task, file, and SSE APIs."""
from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from evaluation.llimit_client.dtos import (
    FileList,
    FileMetadata,
    Task,
    TaskList,
    TaskResult,
    TaskStepList,
)


_DEFAULT_BASE_URL = "http://localhost:8000"

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


def _body_as_text(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


@dataclass
class HttpResponse:
    """Raw HTTP response from the client's HTTP helpers."""

    status_code: int
    headers: httpx.Headers
    content: bytes

    @property
    def text(self) -> str:
        return _body_as_text(self.content)

    def json(self) -> Any:
        return json.loads(self.text)


class LlimitApiError(Exception):
    """Raised when the API returns an unexpected error status."""

    def __init__(self, status_code: int, body_text: str, response: HttpResponse | None = None) -> None:
        self.status_code = status_code
        self.body_text = body_text
        self.response = response
        msg = f"HTTP {status_code}"
        if body_text:
            msg = f"{msg}: {body_text}"
        super().__init__(msg)


@dataclass
class LlimitConfig:
    """Configuration for connecting to a llimit API instance."""

    base_url: str
    api_key: str
    openrouter_api_key: str
    request_timeout: float = 30.0

    @staticmethod
    def from_env(
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        openrouter_api_key: str | None = None,
        request_timeout: float | None = None,
    ) -> LlimitConfig:
        """Build config; non-None keyword arguments override env.

        Environment: LLIMIT_BASE_URL, API_KEY, OPENROUTER_API_KEY, LLIMIT_REQUEST_TIMEOUT.
        """
        return LlimitConfig(
            base_url=(base_url if base_url is not None else os.environ.get("LLIMIT_BASE_URL", _DEFAULT_BASE_URL)),
            api_key=api_key if api_key is not None else os.environ.get("API_KEY", ""),
            openrouter_api_key=(
                openrouter_api_key
                if openrouter_api_key is not None
                else os.environ.get("OPENROUTER_API_KEY", "")
            ),
            request_timeout=(
                request_timeout
                if request_timeout is not None
                else float(os.environ.get("LLIMIT_REQUEST_TIMEOUT", "30"))
            ),
        )


class LlimitClient:
    """Async HTTP client wrapping the llimit task, file, and SSE APIs."""

    def __init__(self, config: LlimitConfig) -> None:
        self._config = config
        base = config.base_url.rstrip("/")
        self._auth_headers = {
            "X-API-Key": config.api_key,
            "X-OpenRouter-API-Key": config.openrouter_api_key,
        }
        self._client = httpx.AsyncClient(
            base_url=base + "/",
            timeout=config.request_timeout,
            headers=self._auth_headers,
        )

    def _path(self, path: str) -> str:
        return path if path.startswith("/") else f"/{path}"

    def _rel(self, path: str) -> str:
        return self._path(path).lstrip("/")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> LlimitClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    def _raise_for_status(self, resp: HttpResponse) -> None:
        if resp.status_code >= 400:
            raise LlimitApiError(resp.status_code, _body_as_text(resp.content), resp)

    def _wrap(self, response: httpx.Response) -> HttpResponse:
        return HttpResponse(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, str]] | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request without a body (e.g. GET)."""
        hdrs = {**self._auth_headers, **(headers or {})}
        response = await self._client.request(
            method,
            self._rel(path),
            params=params,
            headers=hdrs,
        )
        return self._wrap(response)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any,
        params: list[tuple[str, str]] | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request with a JSON-serialized body."""
        hdrs = {**self._auth_headers, **(headers or {})}
        response = await self._client.request(
            method,
            self._rel(path),
            params=params,
            headers=hdrs,
            json=json_body,
        )
        return self._wrap(response)

    async def upload_file(
        self,
        file_path: str | Path,
        *,
        description: str | None = None,
        additional_data: dict[str, Any] | None = None,
        content_type: str | None = None,
    ) -> FileMetadata:
        """Upload a local file and return metadata."""
        path = Path(file_path)
        ct = content_type or _EXTENSION_CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        form: dict[str, str] = {"content_type": ct}
        if description is not None:
            form["description"] = description
        if additional_data is not None:
            form["additional_data"] = json.dumps(additional_data)

        with path.open("rb") as fh:
            httpx_resp = await self._client.post(
                self._rel("/files"),
                files={"file": (path.name, fh, ct)},
                data=form,
            )
        response = self._wrap(httpx_resp)
        self._raise_for_status(response)
        return FileMetadata.from_json(response.json())

    async def register_file_url(
        self,
        *,
        url: str,
        filename: str,
        content_type: str,
        description: str | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> FileMetadata:
        """Register a remote file URL."""
        body: dict[str, Any] = {
            "url": url,
            "filename": filename,
            "content_type": content_type,
        }
        if description is not None:
            body["description"] = description
        if additional_data is not None:
            body["additional_data"] = additional_data
        response = await self.request_json("POST", "/files/url", json_body=body)
        self._raise_for_status(response)
        return FileMetadata.from_json(response.json())

    async def list_files(self) -> FileList:
        """List all files for the current user."""
        response = await self.request("GET", "/files")
        self._raise_for_status(response)
        return FileList.from_json(response.json())

    async def create_task(self, prompt: str, file_ids: list[str] | None = None) -> Task:
        """Create a task and return its initial state."""
        body = {"prompt": prompt, "file_ids": file_ids or []}
        response = await self.request_json("POST", "/task", json_body=body)
        self._raise_for_status(response)
        return Task.from_json(response.json())

    async def list_tasks(self) -> TaskList:
        """List tasks for the current user."""
        response = await self.request("GET", "/task")
        self._raise_for_status(response)
        return TaskList.from_json(response.json())

    async def get_task(self, task_id: str) -> Task:
        """Fetch the current state of a task."""
        response = await self.request("GET", f"/task/{task_id}")
        self._raise_for_status(response)
        return Task.from_json(response.json())

    async def get_task_steps(self, task_id: str) -> TaskStepList:
        """Fetch all steps for a task."""
        response = await self.request("GET", f"/task/{task_id}/steps")
        self._raise_for_status(response)
        return TaskStepList.from_json(response.json())

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = 600.0,
        initial_interval: float = 2.0,
        max_interval: float = 30.0,
        backoff_factor: float = 1.5,
    ) -> TaskResult:
        """Poll a task until it reaches a terminal state or the timeout expires."""
        _TERMINAL = frozenset({"completed", "failed"})

        interval = initial_interval
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            task = await self.get_task(task_id)

            if task.status in _TERMINAL:
                return TaskResult.from_task(task)

            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(
                    f"Task {task_id} did not complete within {timeout:.0f}s "
                    f"(last status: {task.status})"
                )

            await asyncio.sleep(min(interval, remaining))
            interval = min(interval * backoff_factor, max_interval)

    async def stream_events(
        self,
        *,
        event_types: list[str] | None = None,
        metadata_filters: dict[str, list[str]] | None = None,
    ) -> AsyncIterator[str]:
        """Yield raw SSE lines from GET /sse/events (use with 'async for')."""
        params: list[tuple[str, str]] = []
        if event_types:
            for et in event_types:
                params.append(("event_types", et))
        if metadata_filters:
            for key, values in metadata_filters.items():
                for v in values:
                    params.append((key, v))

        req = self._client.build_request("GET", "sse/events", params=params or None)
        response = await self._client.send(req, stream=True)
        try:
            if response.status_code >= 400:
                body = await response.aread()
                hr = HttpResponse(status_code=response.status_code, headers=response.headers, content=body)
                self._raise_for_status(hr)
            async for line in response.aiter_lines():
                yield line
        finally:
            await response.aclose()
