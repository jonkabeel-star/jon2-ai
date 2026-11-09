"""Structural checks for the separate Egyptian Arabic draft and review set."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "data_drafts" / "egyptian_dialogue_draft_01.txt"
EVAL = ROOT / "evaluation" / "egyptian_arabic_prompts_draft.jsonl"


class EgyptianArabicDraftTests(unittest.TestCase):
    def test_dialogue_draft_is_outside_the_training_directory(self):
        self.assertNotEqual(DRAFT.parent, ROOT / "training_data")
        self.assertTrue(DRAFT.is_file())
        text = DRAFT.read_text(encoding="utf-8")
        self.assertIn("DRAFT ONLY: NOT APPROVED FOR TRAINING", text)
        self.assertIn("المستخدم:", text)
        self.assertIn("Jon2:", text)

    def test_dialogue_turns_are_nonempty_and_balanced(self):
        lines = [
            line.strip() for line in DRAFT.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertGreaterEqual(len(lines), 40)
        self.assertEqual(sum(line.startswith("المستخدم:") for line in lines),
                         sum(line.startswith("Jon2:") for line in lines))
        self.assertTrue(all(
            line.startswith(("المستخدم:", "Jon2:")) for line in lines
        ))

    def test_review_prompts_are_valid_unique_jsonl_and_outside_training(self):
        self.assertNotEqual(EVAL.parent, ROOT / "training_data")
        records = [json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines() if line]
        ids = [record["id"] for record in records]
        self.assertGreaterEqual(len(records), 25)
        self.assertEqual(len(ids), len(set(ids)))
        for record in records:
            self.assertTrue(record["prompt"].strip())
            self.assertTrue(record["review_criteria"].strip())

    def test_prompt_builder_never_silently_shortens_current_question(self):
        import sys
        sys.path.insert(0, str(ROOT))
        import chat_engine
        from unittest.mock import Mock

        question = "عايز أفهم بالتفصيل إزاي أبدأ مشروع صغير وأحسب التكلفة والربح"
        tokenizer = Mock()
        tokenizer.encode.side_effect = lambda value: list(value)
        with self.assertRaisesRegex(ValueError, "أطول من نافذة سياق"):
            chat_engine.build_conversation_prompt(
                question, tokenizer=tokenizer, context=40
            )


if __name__ == "__main__":
    unittest.main()
