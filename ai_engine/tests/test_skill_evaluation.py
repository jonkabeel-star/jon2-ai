from __future__ import annotations

import json
import pytest

from ai_engine.skill_evaluation import (
    evaluate_response, load_skill_tasks, summarize_results, validate_skill_task,
)

HASH = "a" * 64


def task(**updates):
    value = {
        "id": "math-001", "domain": "math", "prompt": "What is 2 + 2?",
        "reference_answer": "4", "verifier": "numeric", "tolerance": "0",
        "verification_notes": "Arithmetic independently checked.",
        "source": {"reference": "original reviewed item", "license": "CC0", "sha256": HASH},
        "review_status": "quarantine", "split": "evaluation_only",
    }
    value.update(updates)
    return value


def test_valid_task_stays_evaluation_only_and_quarantined():
    result = validate_skill_task(task())
    assert result["review_status"] == "quarantine"
    assert result["split"] == "evaluation_only"


def test_rejects_non_evaluation_split():
    with pytest.raises(ValueError, match="evaluation_only"):
        validate_skill_task(task(split="training"))


def test_rejects_bad_source_hash():
    with pytest.raises(ValueError, match="sha256"):
        validate_skill_task(task(source={"reference": "x", "license": "x", "sha256": "bad"}))


def test_numeric_answer_with_tolerance():
    item = task(tolerance="0.01")
    assert evaluate_response(item, "4.005")["status"] == "correct"
    assert evaluate_response(item, "4.02")["status"] == "incorrect"


def test_non_numeric_response_is_not_guessed():
    assert evaluate_response(task(), "about four")["status"] == "needs_human_review"


def test_programming_requires_human_review():
    item = task(domain="programming", verifier="human")
    assert evaluate_response(item, "print(2 + 2)")["status"] == "needs_human_review"
    with pytest.raises(ValueError, match="human review"):
        validate_skill_task(task(domain="programming", verifier="exact_text"))


def test_logic_and_science_semantics_are_not_auto_scored():
    for domain in ("logic", "science", "instruction_following"):
        item = task(domain=domain, verifier="human")
        assert evaluate_response(item, "some answer")["status"] == "needs_human_review"


def test_exact_text_only_normalizes_whitespace_and_case():
    item = task(verifier="exact_text", reference_answer="Cairo is the capital.")
    assert evaluate_response(item, "  CAIRO is the capital. ")["status"] == "correct"
    assert evaluate_response(item, "Cairo is the capital of Egypt.")["status"] == "incorrect"


def test_jsonl_loader_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "tasks.jsonl"
    row = json.dumps(task())
    path.write_text(row + "\n" + row + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_skill_tasks(path)


def test_summary_keeps_human_review_separate():
    result = summarize_results([
        {"status": "correct"}, {"status": "incorrect"},
        {"status": "needs_human_review"},
    ])
    assert result == {"correct": 1, "incorrect": 1, "needs_human_review": 1, "total": 3}
