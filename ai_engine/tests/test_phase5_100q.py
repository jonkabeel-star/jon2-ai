"""Structural safeguards for the Phase 5 held-out Arabic benchmark.

These tests validate benchmark integrity only; they do not run or grade Jon2.
"""
import json
import unittest
from pathlib import Path


class PhaseFiveBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "evaluation" / "phase5_prompts_100.jsonl"
        cls.rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_exactly_one_hundred_cases(self):
        self.assertEqual(len(self.rows), 100)

    def test_balanced_msa_and_egyptian(self):
        counts = {}
        for row in self.rows:
            counts[row["language"]] = counts.get(row["language"], 0) + 1
        self.assertEqual(counts, {"msa": 50, "egyptian": 50})

    def test_ids_are_unique_and_prompts_nonempty(self):
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(row["prompt"], str) and row["prompt"].strip() for row in self.rows))

    def test_all_cases_are_evaluation_only(self):
        self.assertTrue(all(row["split"] == "evaluation_only" for row in self.rows))
        self.assertTrue(all(row["training_eligible"] is False for row in self.rows))


if __name__ == "__main__":
    unittest.main()
