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
import dataclasses
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluation.gaia.loader import load_gaia
from evaluation.gaia.models import GaiaConfig, GaiaSample, GaiaSplit
from evaluation.gaia.tools import GaiaTool
from evaluation.gaia.scoring import extract_answer, is_correct
from evaluation.llimit_client.client import LlimitClient, LlimitConfig
from evaluation.llimit_client.dtos import TaskResult

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


@dataclasses.dataclass
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
    cost_usd: float
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

    try:
        file_ids: list[str] = []
        if sample.file_path:
            local_path = Path(data_dir) / sample.file_path
            uploaded = await client.upload_file(local_path)
            file_ids.append(uploaded.id)

        prompt = TASK_PROMPT_TEMPLATE.format(question=sample.question)
        llimit_task_id = (await client.create_task(prompt, file_ids)).id
        task_result = await client.wait_for_task(llimit_task_id, timeout=task_timeout)

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

    return EvalResult(
        gaia_task_id=sample.task_id,
        question=sample.question,
        level=sample.level,
        expected_answer=sample.final_answer,
        predicted_answer=predicted_answer,
        correct=correct,
        task_status=task_result.status if task_result else "error",
        error=error,
        cost_usd=task_result.total_or_cost_usd if task_result else 0.0,
        llimit_task_id=llimit_task_id,
        duration_seconds=round(duration, 2),
    )


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
    """Evaluate all samples concurrently, respecting the worker limit.

    On cancellation, in-flight tasks are cancelled, partial results are saved,
    and CancelledError is re-raised.
    """
    semaphore = asyncio.Semaphore(workers)
    results: list[EvalResult | None] = [None] * len(samples)

    async def _run(index: int, sample: GaiaSample) -> None:
        async with semaphore:
            result = await evaluate_sample(sample, data_dir, client, task_timeout)
            results[index] = result
            _print_result(index + 1, len(samples), sample, result)

    tasks = [asyncio.create_task(_run(i, s)) for i, s in enumerate(samples)]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        partial = [r for r in results if r is not None]
        print(f"\nInterrupted after {len(partial)}/{len(samples)} samples. Saving partial results...")
        _print_and_save(partial, args, output_path)
        raise

    return [r for r in results if r is not None]


def _print_result(
    n: int,
    total: int,
    sample: GaiaSample,
    result: EvalResult,
) -> None:
    status = "CORRECT" if result.correct else "WRONG  "
    error_note = f"  ERROR: {result.error}" if result.error else ""
    print(
        f"[{n:>3}/{total}] {status}  level={sample.level}"
        f"  id={sample.task_id}"
        f"  expected={sample.final_answer!r}"
        f"  got={result.predicted_answer!r}"
        f"  cost=${result.cost_usd:.4f}"
        f"  {result.duration_seconds:.1f}s"
        f"{error_note}"
    )


# ---------------------------------------------------------------------------
# Summary and persistence
# ---------------------------------------------------------------------------


def compute_summary(results: list[EvalResult]) -> dict:
    """Compute aggregate accuracy metrics from evaluation results."""
    total = len(results)
    correct = sum(1 for r in results if r.correct)
    total_cost = sum(r.cost_usd for r in results)

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
        "accuracy": correct / total if total > 0 else 0.0,
        "total_cost_usd": round(total_cost, 6),
        "by_level": level_accuracy,
    }


def _print_and_save(
    results: list[EvalResult],
    args: argparse.Namespace,
    output_path: Path,
) -> None:
    """Print the summary statistics and persist results to disk."""
    summary = compute_summary(results)
    print(f"\n{'=' * 60}")
    print(f"Accuracy: {summary['correct']}/{summary['total']} ({summary['accuracy']:.1%})")
    print(f"Total cost: ${summary['total_cost_usd']:.4f}")
    for lvl, stats in summary["by_level"].items():
        print(f"  Level {lvl}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")
    save_results(results, summary, args, output_path)


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
        "results": [dataclasses.asdict(r) for r in results],
    }
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


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
    print(f"Loading GAIA dataset ({args.dataset_config}, {args.split})...")
    samples, data_dir = load_gaia(config=args.dataset_config, split=args.split)

    before_filter = len(samples)
    samples = [s for s in samples if _is_supported(s)]
    skipped = before_filter - len(samples)
    if skipped:
        print(f"Skipped {skipped} sample(s) with unsupported requirements.")

    if args.shuffle or args.seed is not None:
        seed = args.seed if args.seed is not None else random.randrange(2**32)
        print(f"Shuffling samples with seed={seed}")
        rng = random.Random(seed)
        rng.shuffle(samples)
        args.shuffle = True
        args.seed = seed

    if args.limit is not None:
        samples = samples[: args.limit]

    print(f"Evaluating {len(samples)} samples  (workers={args.workers}, timeout={args.task_timeout}s)\n")

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
