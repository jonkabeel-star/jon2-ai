import tempfile
import unittest
from pathlib import Path

import chat_memory


class ChatMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "memory.sqlite3"
        chat_memory.initialize(self.db)
        self.sid = "123e4567-e89b-42d3-a456-426614174000"

    def tearDown(self):
        self.temp.cleanup()

    def _add_recent_window(self):
        for index in range(chat_memory.RECENT_CONTEXT_RESERVE):
            chat_memory.add_message(
                self.sid, "user", f"رسالة حديثة عادية رقم {index}", self.db
            )

    def test_persists_and_returns_recent_turns_in_order(self):
        chat_memory.add_message(self.sid, "user", "أنا أحب تطوير Jon2", self.db)
        chat_memory.add_message(self.sid, "assistant", "نكمل تطوير المحرك", self.db)
        self.assertEqual(
            chat_memory.recent_messages(self.sid, path=self.db),
            [
                {"role": "user", "content": "أنا أحب تطوير Jon2"},
                {"role": "assistant", "content": "نكمل تطوير المحرك"},
            ],
        )

    def test_retrieves_long_term_memories_outside_recent_context(self):
        chat_memory.add_message(self.sid, "user", "مشروعي اسمه Jon2 وأطوره ببايثون", self.db)
        self._add_recent_window()
        result = chat_memory.relevant_memories(
            self.sid, "كيف أطور مشروع Jon2 ببايثون؟", path=self.db
        )
        self.assertTrue(result)
        self.assertIn("Jon2", result[0]["content"])
        self.assertGreater(result[0]["relevance"], 0)

    def test_recent_turns_are_not_duplicated_as_long_term_memories(self):
        chat_memory.add_message(self.sid, "user", "معلومة حديثة عن Jon2 ببايثون", self.db)
        self.assertEqual(
            chat_memory.relevant_memories(
                self.sid, "Jon2 ببايثون", path=self.db
            ),
            [],
        )

    def test_arabic_alef_variants_match_long_term_memory(self):
        chat_memory.add_message(self.sid, "user", "إزاي أطور مشروعي بالبايثون؟", self.db)
        self._add_recent_window()
        result = chat_memory.relevant_memories(
            self.sid, "ازاي اطور مشروعي بالبايثون؟", path=self.db
        )
        self.assertTrue(result)
        self.assertIn("مشروعي", result[0]["content"])

    def test_add_exchange_persists_both_turns_as_one_exchange(self):
        chat_memory.add_exchange(
            self.sid, "سؤال المستخدم", "إجابة Jon2", self.db
        )
        self.assertEqual(
            chat_memory.recent_messages(self.sid, path=self.db),
            [
                {"role": "user", "content": "سؤال المستخدم"},
                {"role": "assistant", "content": "إجابة Jon2"},
            ],
        )

    def test_add_exchange_rejects_invalid_assistant_before_writing_user(self):
        with self.assertRaises(ValueError):
            chat_memory.add_exchange(self.sid, "سؤال صالح", " ", self.db)
        self.assertEqual(
            chat_memory.session_stats(self.sid, self.db)["message_count"], 0
        )

    def test_clear_removes_all_session_messages(self):
        chat_memory.add_message(self.sid, "user", "مرحبا", self.db)
        chat_memory.clear_session(self.sid, self.db)
        self.assertEqual(chat_memory.session_stats(self.sid, self.db)["message_count"], 0)

    def test_rejects_invalid_session_id(self):
        with self.assertRaises(ValueError):
            chat_memory.add_message("not-a-uuid", "user", "hello", self.db)

    def test_memory_limit_is_clamped(self):
        chat_memory.add_message(self.sid, "user", "مشروع Jon2 ببايثون", self.db)
        self._add_recent_window()
        result = chat_memory.relevant_memories(
            self.sid, "Jon2 ببايثون", limit=999, path=self.db
        )
        self.assertLessEqual(len(result), 8)


if __name__ == "__main__":
    unittest.main()
