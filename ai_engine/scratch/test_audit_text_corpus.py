import tempfile
import unittest
from pathlib import Path
from audit_text_corpus import audit_text

class AuditTextCorpusTests(unittest.TestCase):
    def test_reports_aggregate_counts_without_source_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.txt"
            p.write_text(("هذه فقرة عربية طويلة للاختبار وليست بيانات حقيقية.\n\n" * 2), encoding="utf-8")
            report = audit_text(p)
            self.assertEqual(report["paragraph_count"], 2)
            self.assertEqual(report["unique_paragraph_count"], 1)
            self.assertEqual(report["duplicate_paragraph_count"], 1)
            self.assertGreater(report["arabic_characters"], 0)
            self.assertNotIn("هذه فقرة", str(report))

    def test_detects_contact_pattern_without_echoing_it(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.txt"
            p.write_text("للتواصل test@example.com", encoding="utf-8")
            report = audit_text(p)
            self.assertEqual(report["possible_contact_detail_matches"], 1)
            self.assertNotIn("test@example.com", str(report))

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.txt"
            p.write_text("", encoding="utf-8")
            self.assertTrue(audit_text(p)["empty_file"])

if __name__ == "__main__":
    unittest.main()
