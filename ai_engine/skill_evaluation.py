"""Conservative validation and evaluation for Jon2 skill tasks.

This module does not generate training data, execute submitted code, or claim
semantic understanding. Tasks remain quarantined until rights and human review
are explicitly recorded. Manual domains are never auto-scored.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DOMAINS = {"math", "logic", "science", "programming", "instruction_following"}
VERIFIERS = {"exact_text", "numeric", "human"}
REVIEW_STATES = {"quarantine", "approved", "rejected"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_skill_task(task: object, *, line_number: int | None = None) -> dict[str, Any]:
    """Validate one task record without approving it for training."""
    where = f" on line {line_number}" if line_number is not None else ""
    if not isinstance(task, dict):
        raise ValueError(f"skill task{where} must be a JSON object")
    required = ("id", "domain", "prompt", "reference_answer", "verifier",
                "verification_notes", "source", "review_status", "split")
    missing = [key for key in required if key not in task]
    if missing:
        raise ValueError(f"skill task{where} missing fields: {', '.join(missing)}")
    if not isinstance(task["id"], str) or not task["id"].strip():
        raise ValueError(f"skill task{where} needs a non-empty id")
    if task["domain"] not in DOMAINS:
        raise ValueError(f"skill task{where} has unsupported domain")
    for key in ("prompt", "reference_answer", "verification_notes"):
        if not isinstance(task[key], str) or not task[key].strip():
            raise ValueError(f"skill task{where} field {key!r} must be non-empty text")
    if task["verifier"] not in VERIFIERS:
        raise ValueError(f"skill task{where} has unsupported verifier")
    if task["review_status"] not in REVIEW_STATES:
        raise ValueError(f"skill task{where} has unsupported review_status")
    if task["split"] != "evaluation_only":
        raise ValueError(f"skill task{where} must remain evaluation_only")
    source = task["source"]
    if not isinstance(source, dict):
        raise ValueError(f"skill task{where} source must be an object")
    for key in ("reference", "license", "sha256"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"skill task{where} source needs {key}")
    if not _SHA256.fullmatch(source["sha256"]):
        raise ValueError(f"skill task{where} source sha256 must be 64 lowercase hex characters")
    if task["verifier"] == "numeric":
        try:
            parsed = Decimal(str(task.get("tolerance", "0")))
        except InvalidOperation as exc:
            raise ValueError(f"skill task{where} numeric tolerance is invalid") from exc
        if not parsed.is_finite() or parsed < 0:
            raise ValueError(f"skill task{where} numeric tolerance must be finite and non-negative")
    if task["domain"] == "programming" and task["verifier"] != "human":
        raise ValueError(f"skill task{where} programming answers require human review; code is never executed")
    return task


def load_skill_tasks(path: str | Path) -> list[dict[str, Any]]:
    """Load JSONL tasks and reject duplicate IDs; does not alter source files."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"skill task file not found: {source}")
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
        task = validate_skill_task(record, line_number=line_number)
        if task["id"] in seen:
            raise ValueError(f"duplicate skill task id on line {line_number}: {task['id']}")
        seen.add(task["id"])
        tasks.append(task)
    return tasks


def evaluate_response(task: dict[str, Any], response: str) -> dict[str, Any]:
    """Return a conservative result; ambiguous answers are sent to human review."""
    validate_skill_task(task)
    if not isinstance(response, str) or not response.strip():
        return {"status": "incorrect", "reason": "empty_response"}
    verifier = task["verifier"]
    if verifier == "human":
        return {"status": "needs_human_review", "reason": "semantic_or_code_review_required"}
    if verifier == "exact_text":
        expected = " ".join(task["reference_answer"].split()).casefold()
        actual = " ".join(response.split()).casefold()
        return {"status": "correct" if actual == expected else "incorrect",
                "reason": "normalized_exact_match"}
    try:
        expected_number = Decimal(task["reference_answer"].strip())
        actual_number = Decimal(response.strip())
        tolerance = Decimal(str(task.get("tolerance", "0")))
    except InvalidOperation:
        return {"status": "needs_human_review", "reason": "response_not_unambiguously_numeric"}
    if not all(value.is_finite() for value in (expected_number, actual_number, tolerance)):
        return {"status": "needs_human_review", "reason": "non_finite_numeric_value"}
    correct = abs(actual_number - expected_number) <= tolerance
    return {"status": "correct" if correct else "incorrect", "reason": "numeric_tolerance_check"}


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count outcomes without converting human-review cases into scores."""
    counts = {"correct": 0, "incorrect": 0, "needs_human_review": 0}
    for result in results:
        status = result.get("status")
        if status not in counts:
            raise ValueError(f"unknown evaluation status: {status!r}")
        counts[status] += 1
    return {**counts, "total": len(results)}
