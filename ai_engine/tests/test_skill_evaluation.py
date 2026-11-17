from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.skill_evaluation import (
    evaluate_response,
    load_skill_tasks,
    summarize_results,
    validate_skill_task,
)

HASH = "a" * 64


def make_task(**updates):
    value = {
        "id": "math-001",
        "domain": "math",
        "prompt": "What is 2 + 2?",
        "reference_answer": "4",
        "verifier": "numeric",
        "tolerance": "0",
        "verification_notes": "Arithmetic independently checked.",
        "source": {"reference": "original reviewed item", "license": "CC0", "sha256": HASH},
        "review_status": "quarantine",
        "split": "evaluation_only",
    }
    value.update(updates)
    return value


class SkillEvaluationTests(unittest.TestCase):
    def test_valid_task_stays_evaluation_only_and_quarantined(self):
        result = validate_skill_task(make_task())
        self.assertEqual(result["review_status"], "quarantine")
        self.assertEqual(result["split"], "evaluation_only")

    def test_rejects_non_evaluation_split(self):
        with self.assertRaisesRegex(ValueError, "evaluation_only"):
            validate_skill_task(make_task(split="training"))

    def test_rejects_bad_source_hash(self):
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_skill_task(make_task(
                source={"reference": "x", "license": "x", "sha256": "bad"}
            ))

    def test_numeric_answer_with_tolerance(self):
        item = make_task(tolerance="0.01")
        self.assertEqual(evaluate_response(item, "4.005")["status"], "correct")
        self.assertEqual(evaluate_response(item, "4.02")["status"], "incorrect")

    def test_non_numeric_response_is_not_guessed(self):
        self.assertEqual(
            evaluate_response(make_task(), "about four")["status"],
            "needs_human_review",
        )

    def test_programming_requires_human_review(self):
        item = make_task(domain="programming", verifier="human")
        self.assertEqual(
            evaluate_response(item, "print(2 + 2)")["status"],
            "needs_human_review",
        )
        with self.assertRaisesRegex(ValueError, "human review"):
            validate_skill_task(make_task(domain="programming", verifier="exact_text"))

    def test_logic_and_science_semantics_are_not_auto_scored(self):
        for domain in ("logic", "science", "instruction_following"):
            with self.subTest(domain=domain):
                item = make_task(domain=domain, verifier="human")
                self.assertEqual(
                    evaluate_response(item, "some answer")["status"],
                    "needs_human_review",
                )

    def test_exact_text_only_normalizes_whitespace_and_case(self):
        item = make_task(verifier="exact_text", reference_answer="Cairo is the capital.")
        self.assertEqual(
            evaluate_response(item, "  CAIRO is the capital. ")["status"],
            "correct",
        )
        self.assertEqual(
            evaluate_response(item, "Cairo is the capital of Egypt.")["status"],
            "incorrect",
        )

    def test_jsonl_loader_rejects_duplicate_ids(self):
        row = json.dumps(make_task())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tasks.jsonl"
            path.write_text(row + "\n" + row + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_skill_tasks(path)

    def test_summary_keeps_human_review_separate(self):
        result = summarize_results([
            {"status": "correct"},
            {"status": "incorrect"},
            {"status": "needs_human_review"},
        ])
        self.assertEqual(result, {
            "correct": 1,
            "incorrect": 1,
            "needs_human_review": 1,
            "total": 3,
        })


if __name__ == "__main__":
    unittest.main()
