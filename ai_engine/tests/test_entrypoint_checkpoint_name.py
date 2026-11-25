"""Regression tests ensuring container startup never fetches model weights."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")


class EntrypointCheckpointSelectionTests(unittest.TestCase):
    def test_entrypoint_does_not_use_kaggle_or_external_weight_downloads(self):
        lowered = ENTRYPOINT.lower()
        self.assertNotIn("kaggle", lowered)
        self.assertNotIn("curl", lowered)
        self.assertNotIn("wget", lowered)

    def test_entrypoint_executes_container_command_without_mutating_weights(self):
        self.assertIn('exec "$@"', ENTRYPOINT)
        self.assertNotIn("JON2_CHECKPOINT=", ENTRYPOINT)
        self.assertNotIn("model-weights", ENTRYPOINT)


if __name__ == "__main__":
    unittest.main()
