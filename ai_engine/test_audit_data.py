"""Unit tests for the dependency-free Jon2 training data audit."""
import tempfile
import unittest
from pathlib import Path

from audit_data import audit_dialogue, clean_lines


class AuditDataTests(unittest.TestCase):
    def test_clean_lines_ignores_comments_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("# metadata\n\n  سؤال  \nإجابة\n", encoding="utf-8")
            self.assertEqual(clean_lines(path), ["سؤال", "إجابة"])

    def test_valid_dialogue_has_no_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar.txt"
            path.write_text(
                "المستخدم: مرحبًا\nJon2: أهلًا بك\n"
                "المستخدم: كيف حالك؟\nJon2: بخير\n",
                encoding="utf-8",
            )
            self.assertEqual(audit_dialogue(path), [])

    def test_dialogue_rejects_wrong_turn_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar.txt"
            path.write_text(
                "Jon2: إجابة في غير موضعها\nالمستخدم: سؤال\n",
                encoding="utf-8",
            )
            self.assertEqual(len(audit_dialogue(path)), 2)

    def test_dialogue_rejects_unmatched_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar.txt"
            path.write_text("المستخدم: سؤال بلا إجابة\n", encoding="utf-8")
            errors = audit_dialogue(path)
            self.assertTrue(any("unmatched final turn" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
