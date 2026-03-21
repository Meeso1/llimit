"""Command-line interface for the llimit task and file HTTP API."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from evaluation.llimit_client.client import LlimitApiError, LlimitClient, LlimitConfig
from evaluation.llimit_client.dtos import FileList, FileMetadata, Task, TaskList, TaskStepList, WorkQueueState


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return _jsonable(asdict(obj))
    return obj


def _print_json(data: Any, *, indent: int | None) -> None:
    payload = _jsonable(data)
    if indent is not None:
        print(json.dumps(payload, indent=indent, ensure_ascii=False))
    else:
        print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


def _read_json_file(path: str) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _read_json_stdin() -> dict[str, Any]:
    raw = sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _load_body_json(path: str | None) -> dict[str, Any]:
    if path is None or path == "-":
        return _read_json_stdin()
    return _read_json_file(path)


def _add_client_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--base-url",
        default=None,
        help="API base URL (default: LLIMIT_BASE_URL or http://localhost:8000)",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="X-API-Key (default: LLIMIT_API_KEY)",
    )
    p.add_argument(
        "--openrouter-api-key",
        default=None,
        help="X-OpenRouter-API-Key (default: OPENROUTER_API_KEY)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="HTTP timeout in seconds (default: LLIMIT_REQUEST_TIMEOUT or 30)",
    )


def _config_from_args(args: argparse.Namespace) -> LlimitConfig:
    return LlimitConfig.from_env(
        base_url=args.base_url,
        api_key=args.api_key,
        openrouter_api_key=args.openrouter_api_key,
        request_timeout=args.timeout,
    )


def _print_task_pretty(t: Task) -> None:
    print(f"id:           {t.id}")
    print(f"status:       {t.status}")
    print(f"created_at:   {t.created_at.isoformat()}")
    print(f"completed_at: {t.completed_at.isoformat() if t.completed_at else ''}")
    print(f"title:        {t.title or ''}")
    print(f"steps_gen:    {t.steps_generated}")
    print(f"est_cost_usd: {t.total_estimated_cost_usd}")
    print(f"or_cost_usd:  {t.total_or_cost_usd}")
    print("prompt:")
    print(t.prompt)
    if t.output is not None:
        print("output:")
        print(t.output)


def _print_task_list_pretty(tl: TaskList) -> None:
    if not tl.tasks:
        print("(no tasks)")
        return
    for t in tl.tasks:
        title = (t.title or "").replace("\n", " ")[:60]
        print(f"{t.id}  {t.status:12}  {title}")


def _print_steps_pretty(sl: TaskStepList) -> None:
    print(f"task_id: {sl.task_id}")
    print(f"steps:   {len(sl.steps)}")
    for s in sl.steps:
        print("---")
        print(f"  #{s.step_number}  {s.id}  {s.status}  ({s.step_type})")
        if s.model_name:
            print(f"  model: {s.model_name}")
        if s.output:
            print(f"  output: {s.output[:200]}{'…' if len(s.output) > 200 else ''}")
        if s.failure_reason:
            print(f"  failure: {s.failure_reason}")


def _print_queue_state_pretty(state: WorkQueueState) -> None:
    if state.currently_processing:
        item = state.currently_processing
        started = item.start_time.isoformat() if item.start_time else "?"
        print(f"processing:  [{item.item_type}]  task={item.task_id}  step_number={item.step_number}  started={started}")
    else:
        print("processing:  (none)")

    print(f"pending ({len(state.pending)}):")
    for item in state.pending:
        queued = item.enqueue_time.isoformat() if item.enqueue_time else "?"
        print(f"  [{item.item_type}]  task={item.task_id}  step_number={item.step_number}  queued={queued}")

    if state.stopped_tasks:
        print(f"stopped tasks ({len(state.stopped_tasks)}):")
        for t in state.stopped_tasks:
            title = (t.title or "").replace("\n", " ")[:60]
            print(f"  {t.task_id}  {t.status:12}  {title}")
    else:
        print("stopped tasks: (none)")


def _print_file_pretty(f: FileMetadata) -> None:
    print(f"id:           {f.id}")
    print(f"filename:     {f.filename}")
    print(f"content_type: {f.content_type}")
    print(f"size_bytes:   {f.size_bytes}")
    print(f"url:          {f.url or ''}")
    print(f"description:  {f.description or ''}")
    print(f"created_at:   {f.created_at.isoformat()}")


def _print_file_list_pretty(fl: FileList) -> None:
    if not fl.files:
        print("(no files)")
        return
    for f in fl.files:
        print(f"{f.id}  {f.filename}  {f.content_type}  {f.size_bytes}")


async def cmd_task_create(args: argparse.Namespace) -> int:
    try:
        body = _load_body_json(args.json_path)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2
    if "prompt" not in body:
        print("JSON must include 'prompt'", file=sys.stderr)
        return 2
    file_ids = body.get("file_ids") or []
    if not isinstance(file_ids, list):
        print("'file_ids' must be a list", file=sys.stderr)
        return 2
    file_ids_str = [str(x) for x in file_ids]

    async with LlimitClient(_config_from_args(args)) as client:
        task = await client.create_task(str(body["prompt"]), file_ids_str)

    if args.format == "id":
        print(task.id)
    elif args.format == "json":
        _print_json(task, indent=2 if args.json_indent else None)
    else:
        _print_task_pretty(task)
    return 0


async def cmd_task_list(args: argparse.Namespace) -> int:
    async with LlimitClient(_config_from_args(args)) as client:
        tl = await client.list_tasks()

    if args.format == "json":
        _print_json(tl, indent=2 if args.json_indent else None)
    else:
        _print_task_list_pretty(tl)
    return 0


async def cmd_task_get(args: argparse.Namespace) -> int:
    async with LlimitClient(_config_from_args(args)) as client:
        task = await client.get_task(args.task_id)

    if args.format == "json":
        _print_json(task, indent=2 if args.json_indent else None)
    elif args.format == "id":
        print(task.id)
    elif args.format == "status":
        print(task.status)
    else:
        _print_task_pretty(task)
    return 0


async def cmd_task_steps(args: argparse.Namespace) -> int:
    async with LlimitClient(_config_from_args(args)) as client:
        sl = await client.get_task_steps(args.task_id)

    if args.format == "json":
        _print_json(sl, indent=2 if args.json_indent else None)
    elif args.format == "count":
        print(len(sl.steps))
    else:
        _print_steps_pretty(sl)
    return 0


async def cmd_task_queue(args: argparse.Namespace) -> int:
    async with LlimitClient(_config_from_args(args)) as client:
        state = await client.get_work_queue_state()

    if args.format == "json":
        _print_json(state, indent=2 if args.json_indent else None)
    else:
        _print_queue_state_pretty(state)
    return 0


async def cmd_files_upload(args: argparse.Namespace) -> int:
    path = Path(args.path)
    add_data: dict[str, Any] | None = None
    if args.additional_json:
        try:
            add_raw = _read_json_file(args.additional_json)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 2
        if not isinstance(add_raw, dict):
            print("additional JSON must be an object", file=sys.stderr)
            return 2
        add_data = add_raw

    async with LlimitClient(_config_from_args(args)) as client:
        meta = await client.upload_file(
            path,
            description=args.description,
            additional_data=add_data,
            content_type=args.content_type,
        )

    if args.format == "id":
        print(meta.id)
    elif args.format == "json":
        _print_json(meta, indent=2 if args.json_indent else None)
    else:
        _print_file_pretty(meta)
    return 0


async def cmd_files_register_url(args: argparse.Namespace) -> int:
    try:
        body = _load_body_json(args.json_path)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2
    required = ("url", "filename", "content_type")
    for k in required:
        if k not in body:
            print(f"JSON must include {k!r}", file=sys.stderr)
            return 2
    add = body.get("additional_data")
    if add is not None and not isinstance(add, dict):
        print("'additional_data' must be an object", file=sys.stderr)
        return 2

    async with LlimitClient(_config_from_args(args)) as client:
        meta = await client.register_file_url(
            url=str(body["url"]),
            filename=str(body["filename"]),
            content_type=str(body["content_type"]),
            description=body.get("description"),
            additional_data=add,
        )

    if args.format == "id":
        print(meta.id)
    elif args.format == "json":
        _print_json(meta, indent=2 if args.json_indent else None)
    else:
        _print_file_pretty(meta)
    return 0


async def cmd_files_list(args: argparse.Namespace) -> int:
    async with LlimitClient(_config_from_args(args)) as client:
        fl = await client.list_files()

    if args.format == "json":
        _print_json(fl, indent=2 if args.json_indent else None)
    else:
        _print_file_list_pretty(fl)
    return 0


async def cmd_sse_events(args: argparse.Namespace) -> int:
    metadata: dict[str, list[str]] = {}
    for item in args.filter_kv:
        if "=" not in item:
            print(f"Invalid --filter {item!r}, expected key=value", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        metadata.setdefault(k, []).append(v)

    event_types = args.event_type or None

    async with LlimitClient(_config_from_args(args)) as client:
        try:
            async for line in client.stream_events(
                event_types=event_types,
                metadata_filters=metadata or None,
            ):
                print(line)
        except KeyboardInterrupt:
            print("", file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation.llimit_client",
        description="CLI for llimit task, file, and SSE APIs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # task create
    p_tc = sub.add_parser("task-create", help="POST /task (body: prompt, file_ids)")
    _add_client_args(p_tc)
    p_tc.add_argument(
        "--json-path",
        default="-",
        metavar="PATH",
        help="Path to JSON body, or - for stdin (default: -)",
    )
    p_tc.add_argument(
        "--format",
        choices=("pretty", "json", "id"),
        default="pretty",
        help="Output format",
    )
    p_tc.add_argument(
        "--json-indent",
        action="store_true",
        help="With --format json, pretty-print (2-space indent)",
    )
    p_tc.set_defaults(_run=cmd_task_create)

    # task list
    p_tl = sub.add_parser("task-list", help="GET /task")
    _add_client_args(p_tl)
    p_tl.add_argument(
        "--format",
        choices=("pretty", "json"),
        default="pretty",
    )
    p_tl.add_argument("--json-indent", action="store_true")
    p_tl.set_defaults(_run=cmd_task_list)

    # task get
    p_tg = sub.add_parser("task-get", help="GET /task/{id}")
    _add_client_args(p_tg)
    p_tg.add_argument("task_id", metavar="TASK_ID")
    p_tg.add_argument(
        "--format",
        choices=("pretty", "json", "id", "status"),
        default="pretty",
    )
    p_tg.add_argument("--json-indent", action="store_true")
    p_tg.set_defaults(_run=cmd_task_get)

    # task queue
    p_tq = sub.add_parser("task-queue", help="GET /task/queue — work queue state and stopped tasks")
    _add_client_args(p_tq)
    p_tq.add_argument(
        "--format",
        choices=("pretty", "json"),
        default="pretty",
    )
    p_tq.add_argument("--json-indent", action="store_true")
    p_tq.set_defaults(_run=cmd_task_queue)

    # task steps
    p_ts = sub.add_parser("task-steps", help="GET /task/{id}/steps")
    _add_client_args(p_ts)
    p_ts.add_argument("task_id", metavar="TASK_ID")
    p_ts.add_argument(
        "--format",
        choices=("pretty", "json", "count"),
        default="pretty",
    )
    p_ts.add_argument("--json-indent", action="store_true")
    p_ts.set_defaults(_run=cmd_task_steps)

    # files upload
    p_fu = sub.add_parser("files-upload", help="POST /files (multipart)")
    _add_client_args(p_fu)
    p_fu.add_argument("path", metavar="FILE_PATH")
    p_fu.add_argument("--description", default=None)
    p_fu.add_argument("--content-type", default=None, dest="content_type")
    p_fu.add_argument(
        "--additional-json",
        default=None,
        metavar="PATH",
        help="Path to JSON object merged into additional_data form field",
    )
    p_fu.add_argument(
        "--format",
        choices=("pretty", "json", "id"),
        default="pretty",
    )
    p_fu.add_argument("--json-indent", action="store_true")
    p_fu.set_defaults(_run=cmd_files_upload)

    # files register-url
    p_fr = sub.add_parser("files-register-url", help="POST /files/url")
    _add_client_args(p_fr)
    p_fr.add_argument(
        "--json-path",
        default="-",
        metavar="PATH",
        help="Path to JSON body (url, filename, content_type, ...), or - for stdin",
    )
    p_fr.add_argument(
        "--format",
        choices=("pretty", "json", "id"),
        default="pretty",
    )
    p_fr.add_argument("--json-indent", action="store_true")
    p_fr.set_defaults(_run=cmd_files_register_url)

    # files list
    p_fl = sub.add_parser("files-list", help="GET /files")
    _add_client_args(p_fl)
    p_fl.add_argument(
        "--format",
        choices=("pretty", "json"),
        default="pretty",
    )
    p_fl.add_argument("--json-indent", action="store_true")
    p_fl.set_defaults(_run=cmd_files_list)

    # sse events
    p_se = sub.add_parser("sse-events", help="Stream GET /sse/events until interrupted")
    _add_client_args(p_se)
    p_se.add_argument(
        "--event-type",
        action="append",
        dest="event_type",
        default=[],
        metavar="TYPE",
        help="Repeat to filter by event_types query param",
    )
    p_se.add_argument(
        "--filter",
        action="append",
        dest="filter_kv",
        default=[],
        metavar="KEY=VALUE",
        help="Metadata filter query param (repeatable)",
    )
    p_se.set_defaults(_run=cmd_sse_events)

    return parser


async def _async_main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    runner = args._run
    try:
        return await runner(args)
    except LlimitApiError as exc:
        print(exc, file=sys.stderr)
        return 1
    except httpx.RequestError as exc:
        print(exc, file=sys.stderr)
        return 1


def main() -> None:
    try:
        code = asyncio.run(_async_main())
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
