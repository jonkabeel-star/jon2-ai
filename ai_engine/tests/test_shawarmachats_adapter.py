"""Unit tests for the private ShawarmaChats normalizer."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "datasets" / "adapters" / "ingest_shawarmachats.py"
SPEC = importlib.util.spec_from_file_location("ingest_shawarmachats", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ShawarmaChatsAdapterTests(unittest.TestCase):
    def test_alternating_speakers_become_user_assistant(self):
        turns = [
            {"speaker": "A", "text": "عامل ايه؟"},
            {"speaker": "B", "text": "الحمد لله، تمام."},
            {"speaker": "A", "text": "كويس."},
            {"speaker": "B", "text": "اتفضل."},
        ]
        messages = MODULE._parse_dialogue(turns)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user", "assistant"])
        self.assertEqual(messages[0]["content"], "عامل ايه؟")

    def test_rejects_wrong_turn_order(self):
        with self.assertRaises(ValueError):
            MODULE._parse_dialogue([
                {"speaker": "A", "text": "سؤال"},
                {"speaker": "A", "text": "إجابة"},
            ])

    def test_rejects_odd_number_of_turns(self):
        with self.assertRaises(ValueError):
            MODULE._parse_dialogue([
                {"speaker": "A", "text": "سؤال"},
                {"speaker": "B", "text": "إجابة"},
                {"speaker": "A", "text": "متابعة"},
            ])

    def test_jsonl_writer_records_hash_and_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "training" / "sample.jsonl"
            info = MODULE._write_jsonl(path, [{
                "messages": [
                    {"role": "user", "content": "مرحبا"},
                    {"role": "assistant", "content": "أهلا"},
                ],
            }])
            self.assertEqual(info["records"], 1)
            self.assertGreater(info["size_bytes"], 0)
            self.assertEqual(len(info["sha256"]), 64)
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
