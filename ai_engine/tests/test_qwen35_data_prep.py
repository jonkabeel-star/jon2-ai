"""CPU-only tests for the fail-closed Qwen3.5 Arabic data preparation."""
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from prepare_qwen35_dialogue_data import fingerprint, normalize, parse_file


class Qwen35DataPreparationTests(unittest.TestCase):
    def test_parses_complete_multi_turn_dialogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dialogue.txt"
            path.write_text(
                "# project-authored\n\n"
                "المستخدم: مرحبًا\n"
                "Jon2: أهلًا بك\n"
                "المستخدم: اشرح الفكرة\n"
                "Jon2: سأشرحها ببساطة\n",
                encoding="utf-8",
            )
            rows = parse_file(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual([m["role"] for m in rows[0]["messages"]],
                         ["user", "assistant", "user", "assistant"])

    def test_rejects_repeated_speaker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dialogue.txt"
            path.write_text(
                "المستخدم: سؤال أول\nالمستخدم: سؤال ثان\nJon2: جواب\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                parse_file(path)

    def test_rejects_unknown_nonempty_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dialogue.txt"
            path.write_text(
                "المستخدم: سؤال\nJon2: جواب\nهذا سطر غير مصنف\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                parse_file(path)

    def test_rejects_conversation_not_ending_with_assistant(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dialogue.txt"
            path.write_text("المستخدم: سؤال\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_file(path)

    def test_normalizer_removes_arabic_diacritics_and_spacing_noise(self):
        self.assertEqual(normalize("السَّلَامُ   عَلَيْكُمْ"), normalize("السلام عليكم"))

    def test_fingerprint_is_stable_for_same_message_sequence(self):
        row = {"messages": [
            {"role": "user", "content": "سؤال"},
            {"role": "assistant", "content": "جواب"},
        ]}
        self.assertEqual(fingerprint(row), fingerprint(row.copy()))


if __name__ == "__main__":
    unittest.main()
