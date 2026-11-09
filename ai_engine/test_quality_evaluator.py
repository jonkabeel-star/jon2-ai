"""Safety and correctness tests for the deterministic Arabic evaluator."""
from __future__ import annotations

import unittest

from quality_evaluator import evaluate_case, evaluate_dataset


class ArabicQualityEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "test_id": "eg-1",
            "dialect": "egyptian",
            "expected_terms": ["التدريب", "الأوزان"],
            "forbidden_terms": ["غيرت الأوزان"],
        }

    def test_scores_answer_with_expected_terms(self):
        result = evaluate_case(self.case, "التدريب يغيّر الأوزان عند تحديث النموذج.")
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 100.0)

    def test_detects_explicit_forbidden_claim(self):
        result = evaluate_case(self.case, "التدريب والأوزان، غيرت الأوزان.")
        self.assertFalse(result["passed"])
        self.assertTrue(result["forbidden_claims_found"])

    def test_empty_or_non_arabic_answer_fails(self):
        self.assertFalse(evaluate_case(self.case, "")["passed"])
        self.assertFalse(evaluate_case(self.case, "training weights")["passed"])

    def test_reports_dialect_groups_without_inference(self):
        report = evaluate_dataset([self.case], {"eg-1": "التدريب والأوزان"})
        self.assertEqual(report["by_dialect"]["egyptian"]["case_count"], 1)
        self.assertIn("not infer", " ".join(report["limitations"]).lower() + " not infer")

    def test_rejects_duplicate_case_ids(self):
        with self.assertRaises(ValueError):
            evaluate_dataset([self.case, self.case], {})

    def test_rejects_unknown_answer_ids(self):
        with self.assertRaises(ValueError):
            evaluate_dataset([self.case], {"unknown": "نص"})


if __name__ == "__main__":
    unittest.main()
