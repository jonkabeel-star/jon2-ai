"""Offline safety tests for the private checkpoint downloader."""
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("download_approved_checkpoint.py")
SPEC = importlib.util.spec_from_file_location("jon2_checkpoint_downloader", MODULE_PATH)
assert SPEC and SPEC.loader
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


class CheckpointDownloaderSafetyTests(unittest.TestCase):
    def test_rights_approval_is_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "JON2_MODEL_RIGHTS_APPROVED"):
                downloader.require_yes("JON2_MODEL_RIGHTS_APPROVED")

    def test_only_exact_yes_is_accepted(self):
        for value in ("yes", "true", "1", " YES "):
            with self.subTest(value=value), patch.dict(
                os.environ, {"JON2_MODEL_RIGHTS_APPROVED": value}, clear=True
            ):
                if value == " YES ":
                    downloader.require_yes("JON2_MODEL_RIGHTS_APPROVED")
                else:
                    with self.assertRaises(SystemExit):
                        downloader.require_yes("JON2_MODEL_RIGHTS_APPROVED")

    def test_model_revision_must_be_immutable_sha(self):
        for value in ("main", "latest", "abc123", ""):
            with self.subTest(value=value):
                self.assertIsNone(downloader.SHA_RE.fullmatch(value))

    def test_revision_accepts_40_character_sha(self):
        self.assertIsNotNone(downloader.SHA_RE.fullmatch("a" * 40))


if __name__ == "__main__":
    unittest.main()
