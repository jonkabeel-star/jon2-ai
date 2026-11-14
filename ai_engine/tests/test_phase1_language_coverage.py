"""Tests for phase-1 human-annotated Arabic coverage audit."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ENGINE))
from phase1_language_coverage import build_report


class PhaseOneCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.annotations = self.root / "annotations.jsonl"
        self.source = self.data / "sample.txt"
        self.source.write_text("هذا نص عربي\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def annotate(self, label="egyptian", digest=None):
        import hashlib
        digest = digest or hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.annotations.write_text(json.dumps({
            "file": "sample.txt", "label": label, "sha256": digest,
            "reviewer": "human reviewer", "review_date": "2026-11-14"
        }) + "\n", encoding="utf-8")

    def test_counts_only_human_annotated_arabic(self):
        self.annotate()
        report = build_report(self.data, self.annotations)
        self.assertFalse(report["automatic_dialect_classification"])
        self.assertEqual(report["human_annotated_arabic_characters_by_label"]["egyptian"], 11)
        self.assertEqual(report["coverage_fraction"], 1.0)

    def test_unannotated_source_is_not_guessed(self):
        self.annotations.write_text("", encoding="utf-8")
        report = build_report(self.data, self.annotations)
        self.assertEqual(report["unannotated_files"], ["sample.txt"])
        self.assertEqual(report["human_annotated_arabic_characters"], 0)

    def test_changed_source_invalidates_annotation(self):
        self.annotate()
        self.source.write_text("نص مختلف", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 changed"):
            build_report(self.data, self.annotations)

    def test_invalid_label_is_rejected(self):
        self.annotate("guess")
        with self.assertRaisesRegex(ValueError, "label must"):
            build_report(self.data, self.annotations)


if __name__ == "__main__":
    unittest.main()
