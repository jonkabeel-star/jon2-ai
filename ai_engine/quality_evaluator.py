"""Deterministic, transparent checks for Jon2 Arabic response quality.

This is a screening rubric, not a semantic judge. It checks non-empty output,
annotated concept coverage, and explicitly forbidden claims. Human review and
a capable semantic evaluator remain necessary before accepting model changes.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
DEFAULT_PASS_THRESHOLD = 70


def _normalize(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = re.sub(r"[إأآٱ]", "ا", value)
    value = re.sub(r"[ىي]", "ي", value)
    return re.sub(r"\s+", " ", value).strip()


def evaluate_case(case: dict[str, Any], answer: str) -> dict[str, Any]:
    required = case.get("expected_terms", [])
    forbidden = case.get("forbidden_terms", [])
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise ValueError("expected_terms must be a list of strings")
    if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
        raise ValueError("forbidden_terms must be a list of strings")

    normalized = _normalize(answer)
    matched = [term for term in required if _normalize(term) in normalized]
    violations = [term for term in forbidden if _normalize(term) in normalized]
    nonempty = bool(normalized)
    arabic_chars = len(ARABIC_RE.findall(answer))
    has_arabic = arabic_chars > 0

    coverage = len(matched) / len(required) if required else 1.0
    score = (20 if nonempty else 0) + (60 * coverage) + (20 if not violations else 0)
    if not has_arabic:
        score = min(score, 40)

    return {
        "test_id": str(case.get("test_id", "")),
        "dialect": str(case.get("dialect", "unlabeled")),
        "score": round(score, 2),
        "passed": bool(nonempty and has_arabic and not violations and score >= DEFAULT_PASS_THRESHOLD),
        "nonempty": nonempty,
        "has_arabic_script": has_arabic,
        "matched_terms": matched,
        "missing_terms": [term for term in required if term not in matched],
        "forbidden_claims_found": violations,
        "limitations": [
            "Keyword coverage does not prove semantic correctness.",
            "Dialect label is supplied by the reviewed test case; it is not inferred.",
        ],
    }


def evaluate_dataset(cases: list[dict[str, Any]], answers: dict[str, str]) -> dict[str, Any]:
    if not cases:
        raise ValueError("Evaluation dataset must not be empty")
    ids = [str(case.get("test_id", "")) for case in cases]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("Every case must have a unique non-empty test_id")
    unknown = set(answers) - set(ids)
    if unknown:
        raise ValueError(f"Answers contain unknown test IDs: {sorted(unknown)}")

    results = [
        evaluate_case(case, answers.get(str(case["test_id"]), ""))
        for case in cases
    ]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        groups[result["dialect"]].append(result)

    passed = sum(item["passed"] for item in results)
    return {
        "schema_version": 1,
        "evaluation_type": "deterministic_arabic_screening_not_semantic_validation",
        "case_count": len(results),
        "answered_count": sum(bool(item["nonempty"]) for item in results),
        "passed_count": passed,
        "pass_rate": round(passed / len(results), 4),
        "overall_passed": passed == len(results),
        "by_dialect": {
            dialect: {
                "case_count": len(items),
                "passed_count": sum(item["passed"] for item in items),
                "pass_rate": round(sum(item["passed"] for item in items) / len(items), 4),
            }
            for dialect, items in sorted(groups.items())
        },
        "results": results,
        "limitations": [
            "This rubric detects selected terms and explicit forbidden claims only.",
            "It cannot reliably detect hallucinations, reasoning errors, tone quality, or nuanced dialect fluency.",
            "Do not use this report alone to approve training, checkpoints, or public release.",
        ],
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Each JSONL row must be an object at line {line_number}")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen Jon2 Arabic answers against a reviewed benchmark.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--answers", required=True, help="JSONL objects with test_id and answer")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    cases = load_jsonl(Path(args.cases))
    answer_rows = load_jsonl(Path(args.answers))
    answers: dict[str, str] = {}
    for row in answer_rows:
        test_id, answer = row.get("test_id"), row.get("answer")
        if not isinstance(test_id, str) or not isinstance(answer, str) or test_id in answers:
            parser.error("Answer rows need unique string test_id and string answer fields")
        answers[test_id] = answer
    report = evaluate_dataset(cases, answers)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
