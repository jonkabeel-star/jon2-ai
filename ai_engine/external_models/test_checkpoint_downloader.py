"""Offline safety tests for the private checkpoint downloader."""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("download_approved_checkpoint.py")
SPEC = importlib.util.spec_from_file_location("jon2_checkpoint_downloader", MODULE_PATH)
assert SPEC and SPEC.loader
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)


class CheckpointDownloaderSafetyTests(unittest.TestCase):
    def test_rights_approval_is_required_before_any_download(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "JON2_MODEL_RIGHTS_APPROVED"):
                downloader.main()

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

    def test_hub_terms_approval_is_required(self):
        env = {
            "JON2_MODEL_RIGHTS_APPROVED": "YES",
            "JON2_MODEL_REVISION": "a" * 40,
            "JON2_MODEL_TARGET": "/tmp/jon2-test-checkpoint-target",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(SystemExit, "JON2_HF_ACCESS_ACCEPTED"):
                downloader.main()

    def test_model_revision_must_be_immutable_sha(self):
        for value in ("main", "latest", "abc123", ""):
            with self.subTest(value=value):
                self.assertIsNone(downloader.SHA_RE.fullmatch(value))

    def test_revision_accepts_40_character_sha(self):
        self.assertIsNotNone(downloader.SHA_RE.fullmatch("a" * 40))

    def test_target_inside_repository_is_rejected(self):
        repo_root = MODULE_PATH.resolve().parents[2]
        env = {
            "JON2_MODEL_RIGHTS_APPROVED": "YES",
            "JON2_HF_ACCESS_ACCEPTED": "YES",
            "JON2_MODEL_REVISION": "a" * 40,
            "JON2_MODEL_TARGET": str(repo_root / "unsafe-model-weights"),
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(SystemExit, "must not be stored inside"):
                downloader.main()
        self.assertFalse((repo_root / "unsafe-model-weights").exists())

    def test_nonempty_external_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "checkpoint"
            target.mkdir()
            (target / "keep.txt").write_text("do not overwrite", encoding="utf-8")
            env = {
                "JON2_MODEL_RIGHTS_APPROVED": "YES",
                "JON2_HF_ACCESS_ACCEPTED": "YES",
                "JON2_MODEL_REVISION": "a" * 40,
                "JON2_MODEL_TARGET": str(target),
            }
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(SystemExit, "not empty"):
                    downloader.main()
            self.assertEqual(
                (target / "keep.txt").read_text(encoding="utf-8"),
                "do not overwrite",
            )


if __name__ == "__main__":
    unittest.main()
