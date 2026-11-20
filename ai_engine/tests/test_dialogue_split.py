"""Tests for conversation-level train/validation/test isolation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dialogue_split import split_dialogue_records


def conversation(question, answer, follow_up=None, follow_answer=None):
    messages = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    if follow_up is not None:
        messages.extend([
            {"role": "user", "content": follow_up},
            {"role": "assistant", "content": follow_answer},
        ])
    return {"messages": messages}


class DialogueSplitTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            conversation(f"سؤال مستقل رقم {i}", f"إجابة مستقلة رقم {i}")
            for i in range(30)
        ]

    def test_deterministic(self):
        self.assertEqual(
            split_dialogue_records(self.records, seed=17),
            split_dialogue_records(self.records, seed=17),
        )

    def test_all_records_appear_exactly_once(self):
        parts = split_dialogue_records(self.records)
        self.assertEqual(sum(map(len, parts.values())), len(self.records))
        self.assertEqual(
            sum(len(part) for part in parts.values()),
            len({id(record) for part in parts.values() for record in part}),
        )

    def test_each_partition_is_nonempty(self):
        parts = split_dialogue_records(self.records)
        self.assertTrue(all(parts[name] for name in ("train", "validation", "test")))

    def test_conversations_are_never_fragmented(self):
        multi = conversation("سؤال متعدد", "إجابة أولى", "متابعة", "إجابة متابعة")
        parts = split_dialogue_records(self.records + [multi])
        found = [record for part in parts.values() for record in part if record is multi]
        self.assertEqual(len(found), 1)
        self.assertEqual(len(found[0]["messages"]), 4)

    def test_shared_normalized_question_links_records_into_one_partition(self):
        first = conversation("مَرْحَبًا يا Jon2", "الإجابة الأولى")
        second = conversation("مرحبا يا jon2", "الإجابة الثانية")
        parts = split_dialogue_records(self.records + [first, second])
        locations = {
            name for name, records in parts.items()
            if first in records or second in records
        }
        self.assertEqual(len(locations), 1)

    def test_shared_assistant_text_also_links_records(self):
        first = conversation("سؤال أول", "إجابة مشتركة")
        second = conversation("سؤال ثان", "إجابة مشتركة")
        parts = split_dialogue_records(self.records + [first, second])
        locations = {
            name for name, records in parts.items()
            if first in records or second in records
        }
        self.assertEqual(len(locations), 1)

    def test_too_few_independent_groups_fails_closed(self):
        records = [
            conversation("السؤال نفسه", "إجابة أ"),
            conversation("السؤال نفسه", "إجابة ب"),
            conversation("السؤال نفسه", "إجابة ج"),
        ]
        with self.assertRaisesRegex(ValueError, "three independent"):
            split_dialogue_records(records)

    def test_malformed_conversation_fails_closed(self):
        malformed = {"messages": [
            {"role": "user", "content": "سؤال"},
            {"role": "user", "content": "دور خاطئ"},
        ]}
        with self.assertRaisesRegex(ValueError, "expected assistant"):
            split_dialogue_records(self.records[:2] + [malformed])

    def test_empty_message_fails_closed(self):
        malformed = conversation("سؤال", " ")
        with self.assertRaisesRegex(ValueError, "empty"):
            split_dialogue_records(self.records[:2] + [malformed])


if __name__ == "__main__":
    unittest.main()
