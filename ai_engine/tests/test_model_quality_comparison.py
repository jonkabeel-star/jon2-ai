from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.model_quality_comparison import (
    compare_checkpoints,
    load_reviews,
    validate_review,
)

BASE_HASH = "a" * 64
CANDIDATE_HASH = "b" * 64
AXES = (
    "correctness", "coherence", "arabic_quality",
    "instruction_following", "factuality",
)


def review(model_version, checkpoint_hash, **updates):
    value = {
        "prompt_id": "heldout-001",
        "split": "heldout_evaluation_only",
        "language_variant": "egyptian",
        "model_version": model_version,
        "checkpoint_sha256": checkpoint_hash,
        "reviewer": "reviewer-1",
        "review_date": "2026-11-14",
        "scores": {axis: 3 for axis in AXES},
    }
    value.update(updates)
    return value


class ModelQualityComparisonTests(unittest.TestCase):
    def test_requires_heldout_only_split(self):
        with self.assertRaisesRegex(ValueError, "heldout_evaluation_only"):
            validate_review(review("baseline", BASE_HASH, split="training"))

    def test_rejects_invalid_score(self):
        scores = {axis: 3 for axis in AXES}
        scores["correctness"] = 6
        with self.assertRaisesRegex(ValueError, "1 to 5"):
            validate_review(review("baseline", BASE_HASH, scores=scores))

    def test_rejects_same_checkpoint_hash(self):
        rows = [
            review("baseline", BASE_HASH),
            review("candidate", BASE_HASH),
        ]
        with self.assertRaisesRegex(ValueError, "hashes match"):
            compare_checkpoints(rows)

    def test_rejects_unpaired_prompt(self):
        rows = [review("baseline", BASE_HASH)]
        with self.assertRaisesRegex(ValueError, "not paired"):
            compare_checkpoints(rows)

    def test_reports_candidate_delta_by_axis(self):
        baseline = review("baseline", BASE_HASH)
        candidate_scores = {axis: 4 for axis in AXES}
        candidate_scores["correctness"] = 5
        candidate = review("candidate", CANDIDATE_HASH, scores=candidate_scores)
        report = compare_checkpoints([baseline, candidate])
        self.assertEqual(report["paired_review_count"], 1)
        self.assertEqual(report["mean_score_delta_candidate_minus_baseline"]["correctness"], 2.0)
        self.assertEqual(report["mean_score_delta_candidate_minus_baseline"]["coherence"], 1.0)
        self.assertFalse(report["training_eligible"])

    def test_compares_msa_and_egyptian_separately(self):
        baseline = review("baseline", BASE_HASH)
        candidate = review("candidate", CANDIDATE_HASH)
        msa_base = review("baseline", BASE_HASH, prompt_id="heldout-002", language_variant="msa")
        msa_candidate = review("candidate", CANDIDATE_HASH, prompt_id="heldout-002", language_variant="msa")
        report = compare_checkpoints([baseline, candidate, msa_base, msa_candidate])
        self.assertEqual(
            report["mean_score_delta_by_language_variant"]["egyptian"]["correctness"],
            0.0,
        )
        self.assertEqual(
            report["mean_score_delta_by_language_variant"]["msa"]["correctness"],
            0.0,
        )

    def test_loader_rejects_duplicate_review_rows(self):
        rows = [review("baseline", BASE_HASH), review("baseline", BASE_HASH)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate review"):
                load_reviews(path)


if __name__ == "__main__":
    unittest.main()
