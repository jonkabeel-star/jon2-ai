"""Tests for Arabic character and vocabulary coverage reporting."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_language import analyze_text, analyze_directory


class ArabicCoverageTests(unittest.TestCase):
    def test_reports_full_character_frequency_and_missing_letters(self):
        report = analyze_text("باب بيت ثوب")
        self.assertGreater(report["arabic_letters"], 0)
        self.assertIn("ظ", report["missing_arabic_letters"])
        self.assertEqual(
            sum(x["count"] for x in report["letter_frequencies"]),
            report["arabic_letters"],
        )

    def test_word_normalization_is_for_counts_only(self):
        report = analyze_text("أمل امل أَمَل")
        self.assertEqual(report["unique_normalized_words"], 1)
        self.assertIn("unchanged", report["normalization_note"])

    def test_empty_text_is_safe(self):
        report = analyze_text("")
        self.assertEqual(report["arabic_letters"], 0)
        self.assertEqual(report["lexical_diversity"], 0.0)

    def test_directory_report_ignores_non_txt_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("لغة عربية جميلة", encoding="utf-8")
            (root / "heldout.jsonl").write_text('{"prompt":"اختبار"}', encoding="utf-8")
            report = analyze_directory(root)
            self.assertEqual(len(report["files"]), 1)
            self.assertGreater(report["combined"]["arabic_word_tokens"], 0)

    def test_missing_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                analyze_directory(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
