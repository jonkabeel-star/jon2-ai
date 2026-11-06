import tempfile
import unittest
from pathlib import Path

import chat_memory


class ChatMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "memory.sqlite3"
        chat_memory.initialize(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_persists_and_returns_recent_turns_in_order(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        chat_memory.add_message(sid, "user", "أنا أحب تطوير Jon2", self.db)
        chat_memory.add_message(sid, "assistant", "نكمل تطوير المحرك", self.db)
        self.assertEqual(
            chat_memory.recent_messages(sid, path=self.db),
            [
                {"role": "user", "content": "أنا أحب تطوير Jon2"},
                {"role": "assistant", "content": "نكمل تطوير المحرك"},
            ],
        )

    def test_retrieves_relevant_past_turns(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        chat_memory.add_message(sid, "user", "مشروعي اسمه Jon2 وأطوره ببايثون", self.db)
        chat_memory.add_message(sid, "assistant", "تمام، نكمل", self.db)
        result = chat_memory.relevant_memories(sid, "كيف أطور مشروع Jon2 ببايثون؟", path=self.db)
        self.assertTrue(result)
        self.assertIn("Jon2", result[0]["content"])

    def test_arabic_alef_variants_match_memory_terms(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        chat_memory.add_message(sid, "user", "إزاي أطور مشروعي بالبايثون؟", self.db)
        result = chat_memory.relevant_memories(sid, "ازاي اطور مشروعي بالبايثون؟", path=self.db)
        self.assertTrue(result)
        self.assertIn("مشروعي", result[0]["content"])

    def test_clear_removes_all_session_messages(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        chat_memory.add_message(sid, "user", "مرحبا", self.db)
        chat_memory.clear_session(sid, self.db)
        self.assertEqual(chat_memory.session_stats(sid, self.db)["message_count"], 0)

    def test_rejects_invalid_session_id(self):
        with self.assertRaises(ValueError):
            chat_memory.add_message("not-a-uuid", "user", "hello", self.db)


if __name__ == "__main__":
    unittest.main()
