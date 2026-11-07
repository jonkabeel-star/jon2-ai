"""Tests for loading structured Arabic dialogue training sources."""
import json
import tempfile
import unittest
from pathlib import Path

from jon2_core import read_corpus


class JsonlDialogueLoaderTests(unittest.TestCase):
    def test_loads_user_assistant_turns_as_separate_conversations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = []
            for index in range(20):
                rows.append({
                    "messages": [
                        {"role": "user", "content": f"سؤال عربي رقم {index}: اشرح الفكرة بوضوح."},
                        {"role": "assistant", "content": f"هذه إجابة عربية واضحة للسؤال رقم {index}، مع شرح مختصر ومترابط."},
                    ]
                })
            (root / "dialogue.jsonl").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows),
                encoding="utf-8",
            )
            corpus = read_corpus(root)

        self.assertIn("المستخدم: سؤال عربي رقم 0", corpus)
        self.assertIn("Jon2: هذه إجابة عربية واضحة", corpus)
        self.assertIn("\n\n", corpus)

    def test_rejects_malformed_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dialogue.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid JSONL record"):
                read_corpus(Path(directory))


if __name__ == "__main__":
    unittest.main()
