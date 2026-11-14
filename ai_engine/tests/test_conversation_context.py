"""Tests for multi-turn conversation validation and context packing."""
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ENGINE))
from conversation_context import audit_conversations, format_context, load_conversations, validate_messages


class CharacterEncoder:
    def encode(self, text):
        return list(text)


class ConversationContextTests(unittest.TestCase):
    def test_accepts_multi_turn_alternating_dialogue(self):
        messages = [
            {"role": "user", "content": "احسب 2+2"},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "اضرب الناتج في 3"},
            {"role": "assistant", "content": "12"},
        ]
        self.assertEqual(len(validate_messages(messages)), 4)

    def test_rejects_wrong_role_order_and_empty_content(self):
        with self.assertRaisesRegex(ValueError, "must have role"):
            validate_messages([
                {"role": "user", "content": "سؤال"},
                {"role": "user", "content": "سؤال آخر"},
            ])
        with self.assertRaisesRegex(ValueError, "non-empty"):
            validate_messages([{"role": "user", "content": "   "}])

    def test_inference_history_must_end_with_user(self):
        with self.assertRaisesRegex(ValueError, "current user"):
            validate_messages([
                {"role": "user", "content": "سؤال"},
                {"role": "assistant", "content": "رد"},
            ], require_complete=False)

    def test_context_drops_oldest_whole_pair_and_keeps_current_question(self):
        history = [
            {"role": "user", "content": "قديم جدا"},
            {"role": "assistant", "content": "رد قديم"},
            {"role": "user", "content": "السؤال الحالي مهم"},
        ]
        prompt, dropped = format_context(history, CharacterEncoder(), 60)
        self.assertEqual(dropped, 2)
        self.assertNotIn("قديم جدا", prompt)
        self.assertIn("السؤال الحالي مهم", prompt)
        self.assertTrue(prompt.endswith("Jon2:"))

    def test_raises_instead_of_truncating_current_question(self):
        history = [{"role": "user", "content": "سؤال طويل جدا"}]
        with self.assertRaisesRegex(ValueError, "was preserved"):
            format_context(history, CharacterEncoder(), 4)

    def test_audit_reports_multi_turn_and_duplicates(self):
        one = [{"role": "user", "content": "سؤال"}, {"role": "assistant", "content": "رد"}]
        multi = one + [
            {"role": "user", "content": "متابعة"},
            {"role": "assistant", "content": "توضيح"},
        ]
        report = audit_conversations([one, multi, multi])
        self.assertEqual(report["multi_turn_conversation_count"], 2)
        self.assertEqual(report["duplicate_conversation_count"], 1)
        self.assertFalse(report["semantic_quality_assessed"])

    def test_load_conversations_reports_line_number(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            path.write_text('{"messages":[{"role":"assistant","content":"رد"}]}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Line 1"):
                load_conversations(path)


if __name__ == "__main__":
    unittest.main()
