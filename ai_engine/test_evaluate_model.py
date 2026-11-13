"""Regression tests for the held-out 100-prompt Arabic evaluation suite."""
import json
import tempfile
import unittest
from pathlib import Path

from evaluate_model import load_prompts


class ArabicEvaluationPromptTests(unittest.TestCase):
    def test_repository_suite_contains_exactly_100_unique_prompts(self):
        path = Path(__file__).resolve().parent / "evaluation" / "prompts_ar.jsonl"
        prompts = load_prompts(path)
        self.assertEqual(len(prompts), 100)
        self.assertEqual(len({item["id"] for item in prompts}), 100)
        self.assertTrue(all(item["prompt"].strip() for item in prompts))

    def test_duplicate_prompt_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text(
                json.dumps({"id": "duplicate", "prompt": "سؤال أول"}) + "\\n"
                + json.dumps({"id": "duplicate", "prompt": "سؤال ثان"}) + "\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate evaluation prompt id"):
                load_prompts(path)


if __name__ == "__main__":
    unittest.main()
