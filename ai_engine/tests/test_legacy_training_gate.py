"""Regression tests for the legacy training entry point's safety gate."""
import argparse
import tempfile
import unittest
from pathlib import Path

import jon2_core


class LegacyTrainingGateTests(unittest.TestCase):
    def test_legacy_entry_point_refuses_training_without_private_approval_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "sample.txt").write_text("owner-authored test text", encoding="utf-8")
            args = argparse.Namespace(
                seed=42,
                data=str(data),
                approval_manifest=str(root / "missing-approvals.json"),
                minimum_chars=100_000,
            )
            with self.assertRaises(PermissionError):
                jon2_core.train(args)


if __name__ == "__main__":
    unittest.main()
