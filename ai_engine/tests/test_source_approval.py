"""Unit tests for the source approval gate; no model dependencies required."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from source_approval import validate_source_approvals


class SourceApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "one.txt").write_text("owner-authored sample", encoding="utf-8")
        self.manifest = self.root / "source_approvals.json"

    def tearDown(self):
        self.temp.cleanup()

    def record(self, **overrides):
        item = {
            "file": "one.txt",
            "status": "APPROVED",
            "reviewer": "project-owner",
            "review_date": "2026-11-04",
            "rights_basis": "Original text authored for this project",
            "intended_use": "research_training",
        }
        if "file" in overrides:
            item["file"] = overrides.pop("file")
        source = self.data / item["file"]
        raw = source.read_bytes() if source.is_file() else b""
        item["sha256"] = hashlib.sha256(raw).hexdigest()
        item["character_count"] = len(raw.decode("utf-8"))
        item.update(overrides)
        return item

    def write_manifest(self, records):
        self.manifest.write_text(
            json.dumps({"approved_sources": records}), encoding="utf-8"
        )

    def test_missing_manifest_blocks(self):
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_missing_approval_blocks(self):
        self.write_manifest([])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_non_approved_status_blocks(self):
        self.write_manifest([self.record(status="REVIEW_REQUIRED")])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_empty_required_field_blocks(self):
        self.write_manifest([self.record(rights_basis=" ")])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_invalid_intended_use_blocks(self):
        self.write_manifest([self.record(intended_use="anything")])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_duplicate_approval_blocks(self):
        self.write_manifest([self.record(), self.record()])
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)

    def test_unmatched_approval_blocks(self):
        self.write_manifest([self.record(), self.record(file="missing.txt")])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_path_traversal_blocks(self):
        self.write_manifest([self.record(file="../one.txt")])
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)

    def test_windows_style_backslash_path_blocks(self):
        self.write_manifest([self.record(file="nested\\\\..\\\\one.txt")])
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)

    def test_non_normalized_path_blocks(self):
        self.write_manifest([self.record(file="nested//one.txt")])
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)

    def test_symlink_outside_data_directory_blocks(self):
        outside = self.root / "outside.txt"
        outside.write_text("outside data", encoding="utf-8")
        link = self.data / "linked.txt"
        link.symlink_to(outside)
        self.write_manifest([
            self.record(),
            self.record(file="linked.txt"),
        ])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)


    def test_changed_file_after_approval_blocks(self):
        self.write_manifest([self.record()])
        (self.data / "one.txt").write_text("changed after approval", encoding="utf-8")
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_missing_file_fingerprint_blocks(self):
        record = self.record()
        record.pop("sha256")
        self.write_manifest([record])
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)

    def test_wrong_character_count_blocks(self):
        record = self.record(character_count=999)
        self.write_manifest([record])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_exact_approvals_pass(self):
        (self.data / "nested").mkdir()
        (self.data / "nested" / "two.txt").write_text("second", encoding="utf-8")
        self.write_manifest([self.record(), self.record(file="nested/two.txt")])
        validate_source_approvals(self.data, self.manifest)


if __name__ == "__main__":
    unittest.main()
