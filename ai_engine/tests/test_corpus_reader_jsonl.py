"""Tests for optional structured dialogue corpus ingestion."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from corpus_reader import read_corpus


class JsonlCorpusReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "base.txt").write_text(
            "مقدمة عربية أصلية.\n\nفقرة ثانية مستقلة.", encoding="utf-8"
        )
        (self.root / "dialogue.jsonl").write_text(
            json.dumps({"messages": [
                {"role": "user", "content": "ما عاصمة مصر؟"},
                {"role": "assistant", "content": "عاصمة مصر هي القاهرة."},
            ]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_jsonl_is_excluded_by_default(self):
        corpus = read_corpus(self.root)
        self.assertNotIn("ما عاصمة مصر؟", corpus)

    def test_jsonl_is_added_as_a_complete_conversation(self):
        corpus = read_corpus(self.root, include_jsonl=True)
        self.assertIn("المستخدم: ما عاصمة مصر؟", corpus)
        self.assertIn("Jon2: عاصمة مصر هي القاهرة.", corpus)
        self.assertIn("\\n\\n", corpus)

    def test_malformed_jsonl_is_rejected(self):
        (self.root / "dialogue.jsonl").write_text("{bad json}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid JSONL record"):
            read_corpus(self.root, include_jsonl=True)


if __name__ == "__main__":
    unittest.main()
