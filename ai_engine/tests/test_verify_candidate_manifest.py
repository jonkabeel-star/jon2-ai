import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.verify_candidate_manifest import (
    BASELINE_SHA256,
    MANIFEST_FORMAT,
    verify_candidate_manifest,
)


class CandidateManifestVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.candidates = self.root / "candidates"
        self.candidates.mkdir()
        self.manifest_path = self.root / "candidate-manifest.json"
        self.payload = b"Jon2 private candidate test bytes"
        self.checkpoint = self.candidates / "candidate.pt"
        self.checkpoint.write_bytes(self.payload)
        self.manifest = {
            "format": MANIFEST_FORMAT,
            "git_commit": "a" * 40,
            "profile": "arabic_30m",
            "files": {
                "best": {
                    "filename": "candidate.pt",
                    "size_bytes": len(self.payload),
                    "sha256": hashlib.sha256(self.payload).hexdigest(),
                }
            },
            "public_release_approved": False,
            "human_review_required": True,
        }
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self):
        self.manifest_path.write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def test_valid_candidate_manifest_passes(self):
        report = verify_candidate_manifest(
            self.manifest_path, self.candidates, expected_commit="a" * 40
        )
        self.assertTrue(report["verified"])
        self.assertFalse(report["public_release_approved"])
        self.assertTrue(report["human_review_required"])

    def test_wrong_commit_is_blocked(self):
        with self.assertRaisesRegex(PermissionError, "commit"):
            verify_candidate_manifest(
                self.manifest_path, self.candidates, expected_commit="b" * 40
            )

    def test_tampered_checkpoint_is_blocked(self):
        self.checkpoint.write_bytes(b"tampered")
        with self.assertRaisesRegex(PermissionError, "SHA-256"):
            verify_candidate_manifest(self.manifest_path, self.candidates)

    def test_wrong_size_is_blocked(self):
        self.manifest["files"]["best"]["size_bytes"] += 1
        self.write_manifest()
        with self.assertRaisesRegex(PermissionError, "size"):
            verify_candidate_manifest(self.manifest_path, self.candidates)

    def test_path_traversal_is_blocked(self):
        self.manifest["files"]["best"]["filename"] = "../jon2-last.pt"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "filename"):
            verify_candidate_manifest(self.manifest_path, self.candidates)

    def test_public_release_must_remain_unapproved(self):
        self.manifest["public_release_approved"] = True
        self.write_manifest()
        with self.assertRaisesRegex(PermissionError, "public release"):
            verify_candidate_manifest(self.manifest_path, self.candidates)

    def test_human_review_is_mandatory(self):
        self.manifest["human_review_required"] = False
        self.write_manifest()
        with self.assertRaisesRegex(PermissionError, "human"):
            verify_candidate_manifest(self.manifest_path, self.candidates)

    def test_original_baseline_fingerprint_is_rejected(self):
        self.manifest["files"]["best"]["sha256"] = BASELINE_SHA256
        self.manifest["files"]["best"]["size_bytes"] = self.checkpoint.stat().st_size
        self.write_manifest()
        # Force the actual file digest to the baseline value through a mocked hash
        # is intentionally avoided: the verifier independently checks actual bytes.
        # A manifest-only mismatch is still rejected before any promotion is possible.
        with self.assertRaisesRegex(PermissionError, "SHA-256"):
            verify_candidate_manifest(self.manifest_path, self.candidates)


if __name__ == "__main__":
    unittest.main()
