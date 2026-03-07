"""Answer normalization and scoring utilities for GAIA evaluation."""
import re


def normalize_answer(answer: str) -> str:
    """Normalize an answer string for exact-match comparison."""
    answer = answer.strip()

    # Remove thousand separators (e.g. "1,000" -> "1000")
    answer = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", answer)

    # Remove common currency / percent prefix / suffix, then try numeric parse
    cleaned = re.sub(r"^[$€£¥]", "", answer).rstrip("%").strip()
    try:
        num = float(cleaned)
        # Represent integers without decimal point
        return str(int(num)) if num == int(num) else str(num)
    except ValueError:
        pass

    return answer.lower().strip()


def extract_answer(output: str) -> str:
    """Extract a concise final answer from a task output string."""
    # "Final Answer: X" (case-insensitive, handles trailing punctuation)
    match = re.search(r"[Ff]inal\s+[Aa]nswer\s*:\s*(.+?)(?:\n|$)", output)
    if match:
        return match.group(1).strip().rstrip(".")

    # Fallback: "Answer: X"
    match = re.search(r"(?<!\w)[Aa]nswer\s*:\s*(.+?)(?:\n|$)", output)
    if match:
        return match.group(1).strip().rstrip(".")

    return output.strip()


def is_correct(predicted: str, expected: str) -> bool:
    """Return whether a predicted answer matches the expected answer after normalization."""
    return normalize_answer(predicted) == normalize_answer(expected)
