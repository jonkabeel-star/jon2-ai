import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from download_arabic_candidate import (
    DATASETS,
    build_manifest,
    download_dataset,
    validate_quarantine_destination,
)


class DatasetAcquisitionTests(unittest.TestCase):
    def test_dataset_is_explicitly_quarantined_and_noncommercial(self):
        item = DATASETS["openiti_chunked"]
        self.assertFalse(item["training_eligible"])
        self.assertFalse(item["commercial_use_eligible"])
        self.assertIn("CC BY-NC-SA 4.0", item["upstream_license"])

    def test_rejects_training_data_destination(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "ai_engine" / "training_data" / "candidate"
            with self.assertRaises(ValueError):
                validate_quarantine_destination(target)

    def test_accepts_separate_quarantine_destination(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "Jon2_AI_Quarantine" / "openiti"
            self.assertEqual(validate_quarantine_destination(target), target.resolve())

    def test_download_requires_explicit_large_download_confirmation(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "quarantine"
            with self.assertRaisesRegex(ValueError, "17.9 GB"):
                download_dataset("openiti_chunked", target, confirm_large_download=False)

    def test_manifest_never_approves_training(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            (root_path / "sample.parquet").write_bytes(b"sample")
            manifest = build_manifest("openiti_chunked", root_path, root_path)
            self.assertEqual(manifest["quarantine_status"], "QUARANTINED_NOT_APPROVED")
            self.assertFalse(manifest["training_eligible"])
            self.assertFalse(manifest["commercial_use_eligible"])
            self.assertFalse(manifest["approval_created"])


if __name__ == "__main__":
    unittest.main()
