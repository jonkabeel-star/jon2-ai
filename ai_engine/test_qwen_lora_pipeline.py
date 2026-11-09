import tempfile
import unittest
from pathlib import Path

from finetune_qwen_lora import (
    collect_conversations,
    parse_dialogue_text,
    split_conversations,
)


class DialogueParserTests(unittest.TestCase):
    def test_parses_arabic_user_assistant_pair(self):
        rows = parse_dialogue_text("المستخدم: ازيك؟\nJon2: الحمد لله، أهلاً بيك.")
        self.assertEqual(rows[0][0]["role"], "user")
        self.assertEqual(rows[0][1]["role"], "assistant")
        self.assertEqual(rows[0][1]["content"], "الحمد لله، أهلاً بيك.")

    def test_rejects_unpaired_or_reversed_turns(self):
        with self.assertRaises(ValueError):
            parse_dialogue_text("المستخدم: سؤال فقط")
        with self.assertRaises(ValueError):
            parse_dialogue_text("Jon2: رد قبل السؤال")

    def test_rejects_unknown_lines_instead_of_silently_dropping_them(self):
        with self.assertRaises(ValueError):
            parse_dialogue_text("المستخدم: سؤال\nهذا سطر غير مصنف")

    def test_deduplicates_exact_conversations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "original_dialogue_ar.txt"
            path.write_text(
                "المستخدم: سؤال\nJon2: إجابة\n\nالمستخدم: سؤال\nJon2: إجابة",
                encoding="utf-8",
            )
            self.assertEqual(len(collect_conversations([path])), 1)

    def test_split_is_deterministic_and_disjoint(self):
        conversations = [
            [{"role": "user", "content": f"سؤال {i}"}, {"role": "assistant", "content": f"جواب {i}"}]
            for i in range(40)
        ]
        train_a, val_a = split_conversations(conversations, 0.1, 42)
        train_b, val_b = split_conversations(conversations, 0.1, 42)
        self.assertEqual(train_a, train_b)
        self.assertEqual(val_a, val_b)
        self.assertEqual(len(train_a) + len(val_a), 40)
        self.assertFalse(set(map(str, train_a)) & set(map(str, val_a)))


if __name__ == "__main__":
    unittest.main()
