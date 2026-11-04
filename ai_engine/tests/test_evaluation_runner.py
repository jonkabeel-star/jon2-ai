"""Tests for held-out evaluation prompt validation."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_model import load_prompts, REVIEW_DIMENSIONS


class EvaluationPromptTests(unittest.TestCase):
    def test_loads_valid_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text(
                json.dumps({"id": "one", "prompt": "سؤال"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(load_prompts(path), [{"id": "one", "prompt": "سؤال"}])

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            item = json.dumps({"id": "same", "prompt": "سؤال"})
            path.write_text(item + "\n" + item + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_prompts(path)

    def test_rejects_empty_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text(json.dumps({"id": "one", "prompt": " "}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                load_prompts(path)

    def test_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid JSON"):
                load_prompts(path)

    def test_requires_nonempty_evaluation_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text("# held out prompts only\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                load_prompts(path)

    def test_review_rubric_has_six_dimensions(self):
        self.assertEqual(len(REVIEW_DIMENSIONS), 6)
        self.assertIn("arabic_quality", REVIEW_DIMENSIONS)


if __name__ == "__main__":
    unittest.main()
