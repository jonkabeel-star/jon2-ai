"""Boundary regression tests for private data and exact-file approvals.

Only synthetic fixture text is created here; no repository corpus is read or copied.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from source_approval import validate_source_approvals


class PrivateDataBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "private" / "data"
        self.approvals = self.root / "private" / "approvals" / "source_approvals.json"
        self.data.mkdir(parents=True)
        self.sample = self.data / "fixture.txt"
        self.sample.write_text("synthetic test fixture only", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def record(self):
        raw = self.sample.read_bytes()
        return {
            "file": "fixture.txt",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "character_count": len(raw.decode("utf-8")),
            "status": "APPROVED",
            "reviewer": "test fixture reviewer",
            "review_date": "2026-01-01",
            "rights_basis": "Synthetic test fixture; not a real dataset approval.",
            "intended_use": "research_training",
        }

    def write_manifest(self, records):
        self.approvals.parent.mkdir(parents=True, exist_ok=True)
        self.approvals.write_text(
            json.dumps({"approved_sources": records}), encoding="utf-8"
        )

    def test_external_unapproved_file_is_blocked(self):
        # Data and manifest fixtures are outside the repository checkout.
        self.write_manifest([])
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.approvals)

    def test_changed_external_file_is_blocked_after_exact_approval(self):
        self.write_manifest([self.record()])
        self.sample.write_text("modified synthetic fixture", encoding="utf-8")
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.approvals)

    def test_exact_approval_for_external_fixture_passes(self):
        self.write_manifest([self.record()])
        validate_source_approvals(self.data, self.approvals)


if __name__ == "__main__":
    unittest.main()
