"""Tests for the privacy-conscious dataset inventory."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from dataset_inventory import build_inventory


class DatasetInventoryTests(unittest.TestCase):
    def test_inventory_counts_files_and_tokens_without_text_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            root.mkdir()
            source = "مرحبا بالعالم\nJon2 AI\n"
            (root / "sample.txt").write_text(source, encoding="utf-8")
            report = build_inventory(root, Path(temp) / "missing.json", vocab_size=300)
            self.assertEqual(report["totals"]["files"], 1)
            self.assertEqual(report["totals"]["characters"], len(source))
            self.assertEqual(report["totals"]["bytes"], len(source.encode("utf-8")))
            self.assertEqual(report["files"][0]["sha256"], hashlib.sha256(source.encode()).hexdigest())
            self.assertGreater(report["totals"]["tokens"], 0)
            self.assertNotIn(source, json.dumps(report, ensure_ascii=False))
            self.assertFalse(report["training_permitted"])
            self.assertEqual(report["approval_gate"]["status"], "BLOCKED")
            self.assertEqual(report["files"][0]["provenance"]["status"], "INCOMPLETE")
            self.assertIn("source_url", report["files"][0]["provenance"]["missing_fields"])

    def test_exact_matching_approval_does_not_infer_missing_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            root.mkdir()
            source = "نص عربي أصلي\n"
            raw = source.encode("utf-8")
            (root / "sample.txt").write_bytes(raw)
            manifest = Path(temp) / "approvals.json"
            manifest.write_text(json.dumps({
                "approved_sources": [{
                    "file": "sample.txt",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "character_count": len(source),
                    "status": "APPROVED",
                    "reviewer": "Human reviewer",
                    "review_date": "2026-11-04",
                    "rights_basis": "Project-owned text, verified by reviewer",
                    "intended_use": "research_training",
                }]
            }), encoding="utf-8")
            report = build_inventory(root, manifest, vocab_size=300)
            self.assertTrue(report["training_permitted"])
            self.assertEqual(report["approval_gate"]["status"], "APPROVED")
            self.assertEqual(report["provenance_audit"]["files_with_incomplete_metadata"], 1)
            self.assertEqual(
                report["files"][0]["provenance"]["missing_fields"],
                [
                    "source_url",
                    "publisher",
                    "language",
                    "dialect",
                    "license",
                    "attribution_requirements",
                    "retrieval_date",
                ],
            )

    def test_explicit_provenance_is_reported_with_current_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            root.mkdir()
            source = "مثال عربي للاختبار\n"
            raw = source.encode("utf-8")
            checksum = hashlib.sha256(raw).hexdigest()
            (root / "sample.txt").write_bytes(raw)
            manifest = Path(temp) / "approvals.json"
            manifest.write_text(json.dumps({
                "approved_sources": [{
                    "file": "sample.txt",
                    "sha256": checksum,
                    "character_count": len(source),
                    "status": "APPROVED",
                    "reviewer": "Human reviewer",
                    "review_date": "2026-11-12",
                    "rights_basis": "Explicit written permission verified by reviewer",
                    "intended_use": "research_training",
                    "source_url": "https://example.org/dataset",
                    "publisher": "Example Research Publisher",
                    "language": "ar",
                    "dialect": "Egyptian Arabic",
                    "license": "CC BY 4.0",
                    "attribution_requirements": "Credit the named publisher and link the licence",
                    "retrieval_date": "2026-11-12",
                }]
            }), encoding="utf-8")

            report = build_inventory(root, manifest, vocab_size=300)
            item = report["files"][0]
            provenance = item["provenance"]
            self.assertTrue(report["training_permitted"])
            self.assertEqual(provenance["status"], "COMPLETE")
            self.assertEqual(provenance["missing_fields"], [])
            self.assertEqual(provenance["source_url"], "https://example.org/dataset")
            self.assertEqual(provenance["publisher"], "Example Research Publisher")
            self.assertEqual(provenance["language"], "ar")
            self.assertEqual(provenance["dialect"], "Egyptian Arabic")
            self.assertEqual(provenance["license"], "CC BY 4.0")
            self.assertEqual(provenance["retrieval_date"], "2026-11-12")
            self.assertEqual(provenance["checksum_sha256"], checksum)
            self.assertEqual(provenance["approval_recorded_checksum_sha256"], checksum)
            self.assertEqual(report["provenance_audit"]["files_with_complete_metadata"], 1)

    def test_invalid_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            root.mkdir()
            (root / "bad.txt").write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                build_inventory(root, Path(temp) / "missing.json", vocab_size=256)

    def test_small_vocab_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            root.mkdir()
            (root / "sample.txt").write_text("text", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_inventory(root, Path(temp) / "missing.json", vocab_size=255)


if __name__ == "__main__":
    unittest.main()
