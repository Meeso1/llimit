"""GAIA evaluation runner for the llimit API.

Usage example:
    uv run python evaluation/evaluate.py \\
        --api-key dev-api-key-12345 \\
        --openrouter-api-key sk-or-... \\
        [--base-url http://localhost:8000] \\
        [--dataset-config 2023_level1] \\
        [--split validation] \\
        [--limit 10] \\
        [--workers 5] \\
        [--task-timeout 600] \\
        [--shuffle] \\
        [--seed 42] \\
        [--output evaluation/results/run.json]
"""
import argparse
import asyncio
import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from evaluation.gaia.loader import load_gaia
from evaluation.gaia.models import GaiaConfig, GaiaSample, GaiaSplit
from evaluation.gaia.tools import GaiaTool
from evaluation.gaia.scoring import extract_answer, is_correct
from evaluation.llimit_client.client import LlimitClient, LlimitConfig
from evaluation.llimit_client.dtos import TaskResult

console = Console()

_UNSUPPORTED_TOOLS: set[GaiaTool] = {
    "youtube",
    "web_file_download",
    "python",
    "powerpoint_viewer",
    "google_maps",

}

SUPPORTED_FILE_EXTENSIONS: set[str] = {
    ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".wav", ".mpeg",
    ".mp4", ".mov", ".webm",
    ".txt", ".csv", ".xml", ".py", ".json", ".jsonld",
    ".xlsx", ".docx",
}


def _is_supported(sample: GaiaSample) -> bool:
    """Return True if the sample can be attempted given the system's capabilities."""
    if sample.file_name is not None:
        if Path(sample.file_name).suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
            return False
    if _UNSUPPORTED_TOOLS.intersection(sample.annotator_metadata.tools):
        return False
    return True


TASK_PROMPT_TEMPLATE = (
    "This is an evaluation question:\n\n"
    "{question}\n\n"
    "Your final answer must be a concise value (a number, name, short phrase, etc.).\n"
    "At the very end of your response, write exactly:\n\n"
    "Final Answer: [your answer]\n\n"
    "Response format matters. It might be a good idea to plan a final 'check result' step, to make sure that produced response is in exactly the format that was requested"
)


# ---------------------------------------------------------------------------
# Per-sample evaluation
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Evaluation result for a single GAIA sample."""

    gaia_task_id: str
    question: str
    level: str
    expected_answer: str
    predicted_answer: str | None
    correct: bool
    task_status: str
    error: str | None
    pre_request_estimated_cost_usd: float
    post_request_estimated_cost_usd: float
    or_cost_usd: float
    planning_or_cost_usd: float
    llimit_task_id: str | None
    duration_seconds: float


async def evaluate_sample(
    sample: GaiaSample,
    data_dir: str,
    client: LlimitClient,
    task_timeout: float,
) -> EvalResult:
    """Run a single GAIA sample through llimit and return the evaluation result."""
    start = time.monotonic()
    llimit_task_id: str | None = None
    task_result: TaskResult | None = None
    error: str | None = None

    timed_out = False
    try:
        file_ids: list[str] = []
        if sample.file_path:
            local_path = Path(data_dir) / sample.file_path
            uploaded = await client.upload_file(local_path)
            file_ids.append(uploaded.id)

        prompt = TASK_PROMPT_TEMPLATE.format(question=sample.question)
        llimit_task_id = (await client.create_task(prompt, file_ids)).id
        task_result = await client.wait_for_task(llimit_task_id, timeout=task_timeout)

    except TimeoutError as exc:
        timed_out = True
        error = str(exc)
    except Exception as exc:
        error = str(exc)

    duration = time.monotonic() - start

    predicted_answer: str | None = None
    if task_result is not None and task_result.output:
        predicted_answer = extract_answer(task_result.output)

    correct = (
        is_correct(predicted_answer, sample.final_answer)
        if predicted_answer is not None
        else False
    )

    if task_result is not None:
        task_status = task_result.status
    elif timed_out:
        task_status = "timeout"
    else:
        task_status = "error"

    return EvalResult(
        gaia_task_id=sample.task_id,
        question=sample.question,
        level=sample.level,
        expected_answer=sample.final_answer,
        predicted_answer=predicted_answer,
        correct=correct,
        task_status=task_status,
        error=error,
        pre_request_estimated_cost_usd=task_result.total_pre_request_estimated_cost_usd if task_result else 0.0,
        post_request_estimated_cost_usd=task_result.total_post_request_estimated_cost_usd if task_result else 0.0,
        or_cost_usd=task_result.total_or_cost_usd if task_result else 0.0,
        planning_or_cost_usd=task_result.total_planning_or_cost_usd if task_result else 0.0,
        llimit_task_id=llimit_task_id,
        duration_seconds=round(duration, 2),
    )


# ---------------------------------------------------------------------------
# Live display helpers
# ---------------------------------------------------------------------------


def _is_timed_out(r: EvalResult) -> bool:
    """Return True if the task exceeded the per-task timeout."""
    return r.task_status == "timeout"


def _is_errored(r: EvalResult) -> bool:
    """Return True if the task errored (excluding timeouts and wrong answers)."""
    return not _is_timed_out(r) and (r.error is not None or r.task_status in ("failed", "error"))


@dataclass
class _RunState:
    """Mutable evaluation progress state for the live display."""

    total: int
    in_progress: dict[int, tuple[GaiaSample, float]] = field(default_factory=dict)
    completed: list[tuple[int, GaiaSample, EvalResult]] = field(default_factory=list)


def _render_live(state: _RunState) -> Group:
    """Build the Rich renderable for the live evaluation display."""
    n_done = len(state.completed)
    n_correct = sum(1 for _, _, r in state.completed if r.correct)
    n_timeout = sum(1 for _, _, r in state.completed if _is_timed_out(r) and not r.correct)
    n_error = sum(1 for _, _, r in state.completed if _is_errored(r) and not r.correct)
    n_wrong = n_done - n_correct - n_timeout - n_error

    header = Text()
    header.append(f"Progress: {n_done}/{state.total}   ")
    header.append(f"✓ {n_correct} correct   ", style="bold green")
    header.append(f"✗ {n_wrong} wrong   ", style="bold red")
    header.append(f"⏱ {n_timeout} timeout   ", style="bold magenta")
    header.append(f"! {n_error} error(s)", style="bold yellow")

    parts: list = [header]

    if state.in_progress:
        tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 1))
        tbl.add_column("#", width=5)
        tbl.add_column("lvl", width=3)
        tbl.add_column("question")
        tbl.add_column("elapsed", width=8, justify="right")
        for idx, (sample, start) in sorted(state.in_progress.items()):
            elapsed = time.monotonic() - start
            q = sample.question.replace("\n", " ")
            if len(q) > 70:
                q = q[:70] + "…"
            tbl.add_row(str(idx + 1), sample.level, q, f"{elapsed:.0f}s")
        parts.append(Panel(tbl, title="[cyan]In Progress[/cyan]", border_style="cyan"))

    if state.completed:
        recent = state.completed[-15:]
        tbl2 = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        tbl2.add_column("n", width=9)
        tbl2.add_column("status", width=10)
        tbl2.add_column("lvl", width=3)
        tbl2.add_column("expected", width=22)
        tbl2.add_column("got", width=22)
        tbl2.add_column("cost", width=9)
        tbl2.add_column("dur", width=6, justify="right")
        for idx, sample, r in recent:
            if r.correct:
                badge = Text("✓ CORRECT", style="green")
            elif _is_timed_out(r):
                badge = Text("⏱ TIMEOUT", style="magenta")
            elif _is_errored(r):
                badge = Text("! ERROR  ", style="yellow")
            else:
                badge = Text("✗ WRONG  ", style="red")

            exp = repr(r.expected_answer)
            if len(exp) > 20:
                exp = exp[:19] + "…"

            got_str: str
            if r.predicted_answer is not None:
                got_str = repr(r.predicted_answer)
                if len(got_str) > 20:
                    got_str = got_str[:19] + "…"
            else:
                got_str = "(none)"

            tbl2.add_row(
                f"[{idx + 1:>3}/{state.total}]",
                badge,
                sample.level,
                exp,
                got_str,
                f"${r.or_cost_usd:.4f}",
                f"{r.duration_seconds:.0f}s",
            )
        parts.append(Panel(tbl2, title="Recent Results", border_style="dim"))

    return Group(*parts)


# ---------------------------------------------------------------------------
# Post-completion cost reconciliation
# ---------------------------------------------------------------------------


async def _reconcile_costs(results: list[EvalResult], client: LlimitClient) -> None:
    """Fetch final costs for tasks that completed without a task_result (errors/timeouts).

    Timed-out tasks keep running on the server after we stop waiting; errored tasks may
    have already incurred partial costs. We do a best-effort GET for each such task and
    update both cost fields in-place.
    """
    targets = [r for r in results if r.llimit_task_id is not None and r.or_cost_usd == 0.0]
    if not targets:
        return

    async def _update(r: EvalResult) -> None:
        try:
            task = await client.get_task(r.llimit_task_id)  # type: ignore[arg-type]
            r.pre_request_estimated_cost_usd = task.total_pre_request_estimated_cost_usd
            r.post_request_estimated_cost_usd = task.total_post_request_estimated_cost_usd
            r.or_cost_usd = task.total_or_cost_usd
            r.planning_or_cost_usd = task.total_planning_or_cost_usd
        except Exception:
            pass

    await asyncio.gather(*[_update(r) for r in targets])


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------


async def run_evaluation(
    samples: list[GaiaSample],
    data_dir: str,
    client: LlimitClient,
    task_timeout: float,
    workers: int,
    args: argparse.Namespace,
    output_path: Path,
) -> list[EvalResult]:
    """Evaluate all samples concurrently with a live Rich display."""
    semaphore = asyncio.Semaphore(workers)
    results: list[EvalResult | None] = [None] * len(samples)
    state = _RunState(total=len(samples))

    async def _run(index: int, sample: GaiaSample) -> None:
        async with semaphore:
            state.in_progress[index] = (sample, time.monotonic())
            result = await evaluate_sample(sample, data_dir, client, task_timeout)
            del state.in_progress[index]
            results[index] = result
            state.completed.append((index, sample, result))

    with Live(console=console, refresh_per_second=4) as live:
        async def _refresh_loop() -> None:
            while True:
                live.update(_render_live(state))
                await asyncio.sleep(0.25)

        eval_tasks = [asyncio.create_task(_run(i, s)) for i, s in enumerate(samples)]
        refresh_task = asyncio.create_task(_refresh_loop())
        try:
            await asyncio.gather(*eval_tasks)
            partial = [r for r in results if r is not None]
            await _reconcile_costs(partial, client)
        except asyncio.CancelledError:
            for t in eval_tasks:
                t.cancel()
            await asyncio.gather(*eval_tasks, return_exceptions=True)
            partial = [r for r in results if r is not None]
            await _reconcile_costs(partial, client)
            refresh_task.cancel()
            live.update(_render_live(state))
            console.print(
                f"\n[yellow]Interrupted after {len(partial)}/{len(samples)} samples. "
                f"Saving partial results...[/yellow]"
            )
            _print_and_save(partial, args, output_path)
            raise
        finally:
            refresh_task.cancel()
            live.update(_render_live(state))

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Summary and persistence
# ---------------------------------------------------------------------------


def compute_summary(results: list[EvalResult]) -> dict:
    """Compute aggregate accuracy metrics from evaluation results."""
    total = len(results)
    correct = sum(1 for r in results if r.correct)
    timed_out = sum(1 for r in results if _is_timed_out(r) and not r.correct)
    errored = sum(1 for r in results if _is_errored(r) and not r.correct)
    wrong = total - correct - timed_out - errored
    total_or_cost = sum(r.or_cost_usd for r in results)
    total_planning_or_cost = sum(r.planning_or_cost_usd for r in results)
    total_pre_request_estimated_cost = sum(r.pre_request_estimated_cost_usd for r in results)
    total_post_request_estimated_cost = sum(r.post_request_estimated_cost_usd for r in results)

    by_level: dict[str, dict[str, int]] = {}
    for r in results:
        entry = by_level.setdefault(r.level, {"correct": 0, "total": 0})
        entry["total"] += 1
        if r.correct:
            entry["correct"] += 1

    level_accuracy = {
        lvl: {"correct": v["correct"], "total": v["total"], "accuracy": v["correct"] / v["total"]}
        for lvl, v in sorted(by_level.items())
    }

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "timed_out": timed_out,
        "errored": errored,
        "accuracy": correct / total if total > 0 else 0.0,
        "total_or_cost_usd": round(total_or_cost, 6),
        "total_planning_or_cost_usd": round(total_planning_or_cost, 6),
        "total_pre_request_estimated_cost_usd": round(total_pre_request_estimated_cost, 6),
        "total_post_request_estimated_cost_usd": round(total_post_request_estimated_cost, 6),
        "by_level": level_accuracy,
    }


def _print_and_save(
    results: list[EvalResult],
    args: argparse.Namespace,
    output_path: Path,
) -> None:
    """Print Rich summary tables and persist results to disk."""
    summary = compute_summary(results)

    tbl = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    tbl.add_column("metric", style="bold")
    tbl.add_column("value")
    tbl.add_row(
        "Accuracy",
        f"[bold]{summary['correct']}/{summary['total']}[/bold] ({summary['accuracy']:.1%})",
    )
    tbl.add_row("Wrong answers", str(summary["wrong"]))
    tbl.add_row("Timed out", str(summary["timed_out"]))
    tbl.add_row("Errors", str(summary["errored"]))
    tbl.add_row("Total cost (OpenRouter, steps)", f"${summary['total_or_cost_usd']:.4f}")
    tbl.add_row("Total cost (OpenRouter, planning)", f"${summary['total_planning_or_cost_usd']:.4f}")
    tbl.add_row("Total cost (estimated pre-request)", f"${summary['total_pre_request_estimated_cost_usd']:.4f}")
    tbl.add_row("Total cost (estimated post-request)", f"${summary['total_post_request_estimated_cost_usd']:.4f}")
    for lvl, stats in summary["by_level"].items():
        tbl.add_row(f"  Level {lvl}", f"{stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")
    console.print(Panel(tbl, title="[bold]Evaluation Summary[/bold]", border_style="blue"))

    wrong = [r for r in results if not r.correct and not _is_timed_out(r) and not _is_errored(r)]
    if wrong:
        wt = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        wt.add_column("gaia_task_id", width=36)
        wt.add_column("expected", width=30)
        wt.add_column("got", width=30)
        wt.add_column("or_cost", width=9)
        wt.add_column("dur", width=6, justify="right")
        for r in wrong:
            wt.add_row(
                r.gaia_task_id,
                repr(r.expected_answer),
                repr(r.predicted_answer) if r.predicted_answer is not None else "[dim](none)[/dim]",
                f"${r.or_cost_usd:.4f}",
                f"{r.duration_seconds:.0f}s",
            )
        console.print(Panel(wt, title=f"[red]Wrong Answers ({len(wrong)})[/red]", border_style="red"))

    timeouts = [r for r in results if _is_timed_out(r) and not r.correct]
    if timeouts:
        tt = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        tt.add_column("gaia_task_id", width=36)
        tt.add_column("llimit_task_id", width=36)
        tt.add_column("or_cost", width=9)
        tt.add_column("dur", width=6, justify="right")
        for r in timeouts:
            tt.add_row(
                r.gaia_task_id,
                r.llimit_task_id or "[dim](none)[/dim]",
                f"${r.or_cost_usd:.4f}",
                f"{r.duration_seconds:.0f}s",
            )
        console.print(Panel(tt, title=f"[magenta]Timed Out ({len(timeouts)})[/magenta]", border_style="magenta"))

    errors = [r for r in results if _is_errored(r) and not r.correct]
    if errors:
        et = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        et.add_column("gaia_task_id", width=36)
        et.add_column("status", width=10)
        et.add_column("or_cost", width=9)
        et.add_column("error / reason")
        for r in errors:
            et.add_row(
                r.gaia_task_id,
                r.task_status,
                f"${r.or_cost_usd:.4f}",
                r.error or "[dim](task failed, no output)[/dim]",
            )
        console.print(Panel(et, title=f"[yellow]Errors ({len(errors)})[/yellow]", border_style="yellow"))

    save_results(results, summary, args, output_path)
    console.print(f"\n[dim]Results saved to: {output_path}[/dim]")


def save_results(
    results: list[EvalResult],
    summary: dict,
    args: argparse.Namespace,
    output_path: Path,
) -> None:
    """Save evaluation results and summary to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_config": args.dataset_config,
            "split": args.split,
            "base_url": args.base_url,
            "task_timeout": args.task_timeout,
            "workers": args.workers,
            "limit": args.limit,
            "shuffle": args.shuffle,
            "seed": args.seed if args.shuffle else None,
        },
        "summary": summary,
        "results": [asdict(r) for r in results],
    }
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate llimit on the GAIA benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLIMIT_BASE_URL", "http://localhost:8000"),
        help="Base URL of the llimit API",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LLIMIT_API_KEY", ""),
        required=not os.environ.get("LLIMIT_API_KEY"),
        help="llimit API key (X-API-Key header)",
    )
    parser.add_argument(
        "--openrouter-api-key",
        default=os.environ.get("OPENROUTER_API_KEY", ""),
        required=not os.environ.get("OPENROUTER_API_KEY"),
        help="OpenRouter API key (X-OpenRouter-API-Key header)",
    )
    parser.add_argument(
        "--dataset-config",
        default="2023_level1",
        choices=["2023_level1", "2023_level2", "2023_level3"],
        help="GAIA dataset configuration to use",
    )
    parser.add_argument(
        "--split",
        default="validation",
        choices=["validation", "test"],
        help="Dataset split to evaluate on",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Evaluate only the first N samples",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent tasks",
    )
    parser.add_argument(
        "--task-timeout",
        type=float,
        default=600.0,
        metavar="SECONDS",
        help="Per-task timeout in seconds",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        default=False,
        help="Shuffle samples before evaluating (useful with --limit for random subsets)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Random seed for shuffling (implies --shuffle; random if omitted)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=(
            "Path to write JSON results "
            "(default: evaluation/results/gaia_{config}_{split}_{timestamp}.json)"
        ),
    )
    return parser


async def _async_main(args: argparse.Namespace) -> None:
    console.print(f"Loading GAIA dataset ([bold]{args.dataset_config}[/bold], {args.split})...")
    samples, data_dir = load_gaia(config=args.dataset_config, split=args.split)

    before_filter = len(samples)
    samples = [s for s in samples if _is_supported(s)]
    skipped = before_filter - len(samples)
    if skipped:
        console.print(f"[dim]Skipped {skipped} sample(s) with unsupported requirements.[/dim]")

    if args.shuffle or args.seed is not None:
        seed = args.seed if args.seed is not None else random.randrange(2**32)
        console.print(f"Shuffling samples with seed={seed}")
        rng = random.Random(seed)
        rng.shuffle(samples)
        args.shuffle = True
        args.seed = seed

    if args.limit is not None:
        samples = samples[: args.limit]

    console.print(
        f"Evaluating [bold]{len(samples)}[/bold] samples  "
        f"(workers={args.workers}, timeout={args.task_timeout}s)\n"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(
        args.output
        or f"evaluation/results/gaia_{args.dataset_config}_{args.split}_{timestamp}.json"
    )

    config = LlimitConfig.from_env(
        base_url=args.base_url,
        api_key=args.api_key,
        openrouter_api_key=args.openrouter_api_key,
    )
    async with LlimitClient(config) as client:
        results = await run_evaluation(
            samples, data_dir, client, args.task_timeout, args.workers, args, output_path
        )
    _print_and_save(results, args, output_path)


def main() -> None:
    """Entry point for the GAIA evaluation script."""
    parser = _build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
