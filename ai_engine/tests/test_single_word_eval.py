"""Contract checks for the Arabic single-word evaluation benchmark."""
import json
import unittest
from pathlib import Path


BENCHMARK = (
    Path(__file__).resolve().parents[1]
    / "evaluations"
    / "single_word_arabic_v1.json"
)


class SingleWordBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(BENCHMARK.read_text(encoding="utf-8"))

    def test_benchmark_contains_short_messages(self):
        cases = self.data["cases"]
        self.assertGreaterEqual(len(cases), 10)
        for case in cases:
            self.assertTrue(case["message"].strip())
            self.assertLessEqual(len(case["message"].split()), 2)

    def test_each_case_has_intent_and_human_acceptance_criteria(self):
        for case in self.data["cases"]:
            self.assertTrue(case["intent"])
            self.assertTrue(case["acceptance"])
            self.assertIn("history", case)

    def test_benchmark_is_not_misrepresented_as_training_or_release_approval(self):
        self.assertIn("not training data", self.data["purpose"])
        self.assertIn("human reviewer", self.data["scoring_note"])


if __name__ == "__main__":
    unittest.main()
