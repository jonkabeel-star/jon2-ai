"""Small, dependency-light evaluation utilities for Jon2 Local Model Lab.

This module does not download or load a model. The caller supplies a generate_fn.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Callable, Iterable


def load_jsonl(paths: Iterable[str | Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                required = {"id", "language", "category", "prompt", "review_focus"}
                missing = required.difference(item)
                if missing:
                    raise ValueError(f"{path}:{line_number}: missing {sorted(missing)}")
                rows.append(item)
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate test IDs detected")
    return rows


def run_evaluation(rows: list[dict], generate_fn: Callable[[str], str]) -> list[dict]:
    results = []
    for row in rows:
        started = time.perf_counter()
        try:
            answer = generate_fn(row["prompt"])
            error = ""
        except Exception as exc:  # preserve failed case for audit
            answer = ""
            error = f"{type(exc).__name__}: {exc}"
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        results.append({
            **row,
            "answer": answer,
            "latency_ms": elapsed_ms,
            "runtime_error": error,
            "human_correctness_1_5": "",
            "human_language_quality_1_5": "",
            "human_hallucination_yes_no": "",
            "human_abstention_appropriate_yes_no": "",
            "review_notes": "",
        })
    return results


def write_report(results: list[dict], output_dir: str | Path) -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "baseline_results.json"
    csv_path = output / "baseline_results_for_review.csv"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    fields = list(results[0].keys()) if results else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(results)
    return json_path, csv_path
