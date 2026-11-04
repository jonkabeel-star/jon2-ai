"""Tests for tokenizer efficiency and byte-fallback reporting."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_tokenizer import analyze_text, analyze_directory


class TokenizerAuditTests(unittest.TestCase):
    def test_report_counts_byte_and_merged_tokens(self):
        report = analyze_text("العربية العربية العربية " * 8, vocab_size=320)
        corpus = report["corpus"]
        self.assertGreater(report["actual_vocab_size"], 256)
        self.assertEqual(
            corpus["byte_fallback_tokens"] + corpus["merged_tokens"],
            corpus["tokens"],
        )
        self.assertTrue(corpus["round_trip_exact"])
        self.assertGreaterEqual(corpus["byte_fallback_percentage"], 0.0)
        self.assertLessEqual(corpus["byte_fallback_percentage"], 100.0)

    def test_unseen_emoji_and_scripts_round_trip(self):
        report = analyze_text("نص عربي " * 8, vocab_size=300)
        self.assertTrue(report["all_samples_round_trip_exact"])
        self.assertEqual(len(report["sample_suites"]), 4)

    def test_empty_corpus_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_text("   ")

    def test_directory_uses_only_txt_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("لغة عربية " * 4, encoding="utf-8")
            (root / "heldout.jsonl").write_text('{"text":"لا يدخل"}', encoding="utf-8")
            report = analyze_directory(root, vocab_size=300)
            self.assertEqual(report["source_file_count"], 1)
            self.assertEqual(report["source_files"][0]["file"], "a.txt")
            self.assertTrue(report["all_samples_round_trip_exact"])

    def test_missing_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                analyze_directory(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
