"""Regression tests for Jon2's SQLite conversation memory.

Run with: python -m unittest discover -s tests -v
These tests use temporary databases and never touch a production memory store.
"""
import tempfile
import unittest
import uuid
from pathlib import Path

from ai_engine import chat_memory


class ChatMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.sqlite3"
        self.session_a = str(uuid.uuid4())
        self.session_b = str(uuid.uuid4())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_exchange_is_persisted_as_ordered_user_assistant_pair(self):
        chat_memory.add_exchange(
            self.session_a, "مرحبا", "أهلا بك", path=self.db_path
        )
        messages = chat_memory.recent_messages(
            self.session_a, limit=8, path=self.db_path
        )
        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "مرحبا"},
                {"role": "assistant", "content": "أهلا بك"},
            ],
        )

    def test_sessions_are_isolated(self):
        chat_memory.add_exchange(
            self.session_a, "سر خاص", "رد خاص", path=self.db_path
        )
        self.assertEqual(
            chat_memory.recent_messages(
                self.session_b, limit=8, path=self.db_path
            ),
            [],
        )

    def test_recent_messages_respects_limit_and_keeps_chronological_order(self):
        for index in range(5):
            chat_memory.add_message(
                self.session_a, "user", f"رسالة {index}", path=self.db_path
            )
        messages = chat_memory.recent_messages(
            self.session_a, limit=2, path=self.db_path
        )
        self.assertEqual(
            [item["content"] for item in messages],
            ["رسالة 3", "رسالة 4"],
        )

    def test_relevant_memories_only_returns_matching_older_messages(self):
        chat_memory.add_exchange(
            self.session_a,
            "مشروع Jon2 يستخدم محرك ذاكرة SQLite",
            "ذاكرة Jon2 تحفظ المحادثات في SQLite",
            path=self.db_path,
        )
        # Add enough newer turns to move the matching exchange outside the
        # eight-message recent-context window supplied separately to the model.
        for index in range(5):
            chat_memory.add_exchange(
                self.session_a,
                f"موضوع عام {index}",
                f"تفاصيل عامة {index}",
                path=self.db_path,
            )
        results = chat_memory.relevant_memories(
            self.session_a, "ذاكرة Jon2 SQLite", limit=4, path=self.db_path
        )
        self.assertTrue(results)
        self.assertTrue(
            any("SQLite" in item["content"] for item in results)
        )

    def test_clear_session_deletes_only_selected_session(self):
        chat_memory.add_exchange(
            self.session_a, "أ", "ب", path=self.db_path
        )
        chat_memory.add_exchange(
            self.session_b, "ج", "د", path=self.db_path
        )
        chat_memory.clear_session(self.session_a, path=self.db_path)
        self.assertEqual(
            chat_memory.session_stats(self.session_a, path=self.db_path)[
                "message_count"
            ],
            0,
        )
        self.assertEqual(
            chat_memory.session_stats(self.session_b, path=self.db_path)[
                "message_count"
            ],
            2,
        )

    def test_invalid_session_id_is_rejected(self):
        with self.assertRaises(ValueError):
            chat_memory.recent_messages(
                "not-a-uuid", path=self.db_path
            )

    def test_empty_or_oversized_message_is_rejected(self):
        with self.assertRaises(ValueError):
            chat_memory.add_message(
                self.session_a, "user", " ", path=self.db_path
            )
        with self.assertRaises(ValueError):
            chat_memory.add_message(
                self.session_a,
                "user",
                "x" * (chat_memory.MAX_CONTENT_CHARS + 1),
                path=self.db_path,
            )


if __name__ == "__main__":
    unittest.main()
