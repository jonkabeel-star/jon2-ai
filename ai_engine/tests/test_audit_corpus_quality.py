"""Tests for privacy-aware corpus quality reporting."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_corpus_quality import analyze_text, analyze_directory, normalize_line


class CorpusQualityAuditTests(unittest.TestCase):
    def test_language_mix_and_length_statistics(self):
        report = analyze_text("مرحبا بالعالم. Hello world!\nهذا سطر عربي آخر.")
        self.assertGreater(report["language_mix"]["arabic_letters"], 0)
        self.assertGreater(report["language_mix"]["latin_letters"], 0)
        self.assertLessEqual(report["language_mix"]["arabic_percentage_of_letters"], 100.0)
        self.assertLessEqual(report["language_mix"]["latin_percentage_of_letters"], 100.0)
        self.assertLessEqual(
            report["language_mix"]["arabic_letters"] + report["language_mix"]["latin_letters"],
            report["language_mix"]["letters_total"],
        )
        self.assertEqual(report["line_length_characters"]["count"], 2)
        self.assertGreaterEqual(report["sentence_length_characters"]["count"], 2)

    def test_duplicate_detection_normalizes_unicode_and_whitespace(self):
        self.assertEqual(normalize_line("  أمل   جميل "), normalize_line("أمل جميل"))
        report = analyze_text("أمل جميل\n  أمل   جميل ")
        self.assertEqual(report["duplicate_lines"]["normalized_duplicate_groups"], 1)
        self.assertEqual(report["duplicate_lines"]["excess_duplicate_lines"], 1)

    def test_privacy_signals_report_counts_without_values(self):
        report = analyze_text("Contact test.person@example.com or +1 202 555 0198")
        signals = report["privacy_review_signals"]
        self.assertEqual(signals["email_like_matches"], 1)
        self.assertGreaterEqual(signals["phone_like_matches"], 1)
        rendered = str(report)
        self.assertNotIn("test.person@example.com", rendered)
        self.assertNotIn("+1 202 555 0198", rendered)

    def test_iso_calendar_dates_are_not_flagged_as_phone_numbers(self):
        report = analyze_text("# Authored for this project on 2026-11-04.\nنص عربي")
        self.assertEqual(report["privacy_review_signals"]["phone_like_matches"], 0)
        self.assertFalse(any("personal contact information" in item for item in report["warnings"]))

    def test_phone_like_number_is_still_flagged_without_exposing_value(self):
        report = analyze_text("مثال توضيحي: 01012345678")
        self.assertEqual(report["privacy_review_signals"]["phone_like_matches"], 1)
        self.assertNotIn("01012345678", str(report))

    def test_integrity_signals_and_empty_text(self):
        report = analyze_text("نص\u200b تالف\ufffd\n")
        self.assertEqual(report["integrity_signals"]["unicode_replacement_characters"], 1)
        self.assertEqual(report["integrity_signals"]["zero_width_or_bom_characters"], 1)
        self.assertTrue(report["warnings"])
        empty = analyze_text("")
        self.assertEqual(empty["non_empty_lines"], 0)
        self.assertIn("Source is empty.", empty["warnings"])

    def test_directory_is_recursive_and_txt_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("نص عربي", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "b.txt").write_text("English text", encoding="utf-8")
            (root / "ignore.jsonl").write_text('{"text":"ignored"}', encoding="utf-8")
            report = analyze_directory(root)
            self.assertEqual(report["file_count"], 2)
            self.assertEqual(
                {item["source"] for item in report["files"]},
                {"a.txt", "nested/b.txt"},
            )

    def test_directory_rejects_file_symlink_outside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            root = workspace / "corpus"
            root.mkdir()
            outside = workspace / "private.txt"
            outside.write_text("must not be inspected", encoding="utf-8")
            link = root / "external.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable in this environment")
            with self.assertRaises(PermissionError):
                analyze_directory(root)

    def test_invalid_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.txt").write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                analyze_directory(root)

    def test_missing_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                analyze_directory(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
