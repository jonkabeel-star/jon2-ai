"""Human-reviewed paired quality comparisons for Jon2 checkpoints.

This is an evaluation/reporting tool only. It never loads a checkpoint, runs
inference, modifies weights, or promotes a candidate model.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

_AXES = (
    "correctness",
    "coherence",
    "arabic_quality",
    "instruction_following",
    "factuality",
)
_VARIANTS = {"msa", "egyptian", "mixed"}
_VERSIONS = {"baseline", "candidate"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_review(record: object, *, line_number: int | None = None) -> dict[str, Any]:
    where = f" on line {line_number}" if line_number is not None else ""
    if not isinstance(record, dict):
        raise ValueError(f"review{where} must be a JSON object")
    required = (
        "prompt_id", "split", "language_variant", "model_version",
        "checkpoint_sha256", "reviewer", "review_date", "scores",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"review{where} missing fields: {', '.join(missing)}")
    for key in ("prompt_id", "reviewer", "review_date"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"review{where} field {key!r} must be non-empty text")
    if record["split"] != "heldout_evaluation_only":
        raise ValueError(f"review{where} must use heldout_evaluation_only split")
    if record["language_variant"] not in _VARIANTS:
        raise ValueError(f"review{where} has unsupported language_variant")
    if record["model_version"] not in _VERSIONS:
        raise ValueError(f"review{where} model_version must be baseline or candidate")
    if not isinstance(record["checkpoint_sha256"], str) or not _SHA256.fullmatch(record["checkpoint_sha256"]):
        raise ValueError(f"review{where} checkpoint_sha256 must be 64 lowercase hex characters")
    scores = record["scores"]
    if not isinstance(scores, dict) or set(scores) != set(_AXES):
        raise ValueError(f"review{where} scores must contain exactly: {', '.join(_AXES)}")
    for axis, score in scores.items():
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"review{where} score {axis!r} must be an integer from 1 to 5")
    if "notes" in record and not isinstance(record["notes"], str):
        raise ValueError(f"review{where} notes must be text when supplied")
    return record


def load_reviews(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"review file not found: {source}")
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
        item = validate_review(record, line_number=line_number)
        key = (item["prompt_id"], item["model_version"], item["reviewer"])
        if key in seen:
            raise ValueError(f"duplicate review for prompt/model/reviewer on line {line_number}")
        seen.add(key)
        records.append(item)
    if not records:
        raise ValueError("review file contains no records")
    return records


def compare_checkpoints(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare only paired prompt/reviewer/variant records on identical held-out items."""
    if not records:
        raise ValueError("at least one review record is required")
    validated = [validate_review(item) for item in records]
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in validated:
        key = (item["prompt_id"], item["reviewer"], item["language_variant"])
        if item["model_version"] in grouped[key]:
            raise ValueError(f"duplicate model version for paired review: {key[0]}")
        grouped[key][item["model_version"]] = item
    unpaired = [key[0] for key, pair in grouped.items() if set(pair) != _VERSIONS]
    if unpaired:
        raise ValueError(f"baseline/candidate reviews are not paired for prompts: {', '.join(sorted(unpaired))}")
    for key, pair in grouped.items():
        if pair["baseline"]["checkpoint_sha256"] == pair["candidate"]["checkpoint_sha256"]:
            raise ValueError(f"baseline and candidate checkpoint hashes match for prompt {key[0]}")

    deltas: dict[str, list[int]] = {axis: [] for axis in _AXES}
    by_variant: dict[str, dict[str, list[int]]] = {
        variant: {axis: [] for axis in _AXES} for variant in _VARIANTS
    }
    for key, pair in grouped.items():
        variant = key[2]
        for axis in _AXES:
            delta = pair["candidate"]["scores"][axis] - pair["baseline"]["scores"][axis]
            deltas[axis].append(delta)
            by_variant[variant][axis].append(delta)

    return {
        "paired_review_count": len(grouped),
        "heldout_only": True,
        "training_eligible": False,
        "mean_score_delta_candidate_minus_baseline": {
            axis: round(mean(values), 4) for axis, values in deltas.items()
        },
        "mean_score_delta_by_language_variant": {
            variant: {
                axis: round(mean(values), 4) if values else None
                for axis, values in axes.items()
            }
            for variant, axes in by_variant.items()
        },
        "notice": (
            "Human-reviewed paired scores are descriptive evidence, not proof of "
            "general understanding. Do not use held-out prompts or outputs for training."
        ),
    }
