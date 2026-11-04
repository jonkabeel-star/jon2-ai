import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai_engine"))

from train_jon2 import validate_source_approvals


class SourceApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "owned.txt").write_text("sample Arabic text", encoding="utf-8")
        self.manifest = self.root / "source_approvals.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, record):
        self.manifest.write_text(
            json.dumps({"approved_sources": [record]}, ensure_ascii=False),
            encoding="utf-8",
        )

    def approved_record(self):
        return {
            "file": "owned.txt",
            "status": "APPROVED",
            "reviewer": "Test reviewer",
            "review_date": "2026-11-04",
            "rights_basis": "Project-owned sample created for this test",
            "intended_use": "research_training",
        }

    def test_missing_manifest_blocks(self):
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_pending_source_blocks(self):
        record = self.approved_record()
        record["status"] = "NOT REVIEWED"
        self.write_manifest(record)
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_explicit_approval_passes(self):
        self.write_manifest(self.approved_record())
        validate_source_approvals(self.data, self.manifest)

    def test_missing_source_record_blocks(self):
        self.write_manifest({
            "file": "another.txt",
            "status": "APPROVED",
            "reviewer": "Test reviewer",
            "review_date": "2026-11-04",
            "rights_basis": "Test",
            "intended_use": "research_training",
        })
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest)

    def test_path_traversal_blocks(self):
        record = self.approved_record()
        record["file"] = "../owned.txt"
        self.write_manifest(record)
        with self.assertRaises(ValueError):
            validate_source_approvals(self.data, self.manifest)


if __name__ == "__main__":
    unittest.main()
