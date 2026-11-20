"""Regression tests for the private, mounted Jon2 checkpoint entrypoint."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")


class PrivateCheckpointEntrypointTests(unittest.TestCase):
    def test_default_checkpoint_is_the_private_original_checkpoint(self):
        self.assertIn('${JON2_CHECKPOINT:-/app/model-weights/jon2-last.pt}', ENTRYPOINT)

    def test_checkpoint_path_and_expected_digest_are_exported(self):
        self.assertIn('export JON2_CHECKPOINT="$CHECKPOINT_PATH"', ENTRYPOINT)
        self.assertIn('export JON2_CHECKPOINT_SHA256="$EXPECTED_SHA256"', ENTRYPOINT)
        self.assertIn('JON2_CHECKPOINT_SHA256:-edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2', ENTRYPOINT)

    def test_missing_private_checkpoint_keeps_api_health_only(self):
        self.assertIn('if [ ! -s "$CHECKPOINT_PATH" ]; then', ENTRYPOINT)
        self.assertIn('health-only mode; chat release remains closed', ENTRYPOINT)

    def test_checkpoint_hash_mismatch_stops_container(self):
        self.assertIn('if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then', ENTRYPOINT)
        self.assertIn('exit 1', ENTRYPOINT)

    def test_entrypoint_does_not_download_from_kaggle(self):
        self.assertNotIn('kaggle', ENTRYPOINT.lower())
        self.assertNotIn('KAGGLE_API_TOKEN', ENTRYPOINT)


if __name__ == "__main__":
    unittest.main()
