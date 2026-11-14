"""Tests for exact held-out evaluation prompt leakage audit."""
import json
import tempfile
import unittest
from pathlib import Path

from audit_evaluation_leakage import audit_overlap, normalize_prompt


class EvaluationLeakageTests(unittest.TestCase):
    def test_normalization_handles_unicode_and_whitespace(self):
        self.assertEqual(normalize_prompt("  أَهْلًا   بالعالم "), normalize_prompt("أَهْلًا بالعالم"))

    def test_detects_exact_prompt_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            training = root / "training"
            training.mkdir()
            (training / "sample.txt").write_text("اشرح الذكاء الاصطناعي ببساطة", encoding="utf-8")
            evaluation = root / "eval.jsonl"
            evaluation.write_text(json.dumps({
                "id": "heldout_1", "prompt": "اشرح الذكاء الاصطناعي ببساطة"
            }, ensure_ascii=False) + "\\n", encoding="utf-8")
            report = audit_overlap(training, [evaluation])
            self.assertEqual(report["status"], "OVERLAP_FOUND")
            self.assertEqual(report["exact_normalized_prompt_matches"][0]["id"], "heldout_1")

    def test_allows_nonmatching_prompt_and_does_not_mutate_training(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            training = root / "training"
            training.mkdir()
            source = training / "sample.txt"
            source.write_text("نص تدريب مختلف تمامًا", encoding="utf-8")
            before = source.read_bytes()
            evaluation = root / "eval.jsonl"
            evaluation.write_text(json.dumps({
                "id": "heldout_2", "prompt": "سؤال اختبار مستقل"
            }, ensure_ascii=False) + "\\n", encoding="utf-8")
            report = audit_overlap(training, [evaluation])
            self.assertEqual(report["status"], "NO_EXACT_PROMPT_OVERLAP")
            self.assertEqual(source.read_bytes(), before)

    def test_rejects_duplicate_evaluation_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            training = root / "training"
            training.mkdir()
            (training / "sample.txt").write_text("محتوى", encoding="utf-8")
            evaluation = root / "eval.jsonl"
            rows = [
                {"id": "same", "prompt": "السؤال الأول"},
                {"id": "same", "prompt": "السؤال الثاني"},
            ]
            evaluation.write_text("".join(json.dumps(row, ensure_ascii=False) + "\\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate evaluation prompt id"):
                audit_overlap(training, [evaluation])


if __name__ == "__main__":
    unittest.main()
