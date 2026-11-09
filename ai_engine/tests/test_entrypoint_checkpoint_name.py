"""Regression tests for selecting the deployed Jon2 checkpoint by configured path."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")


class EntrypointCheckpointSelectionTests(unittest.TestCase):
    def test_default_checkpoint_remains_backward_compatible(self):
        self.assertIn('${JON2_CHECKPOINT:-/app/model-weights/jon2-small.pt}', ENTRYPOINT)

    def test_runtime_filename_is_derived_from_configured_checkpoint_path(self):
        self.assertIn('CHECKPOINT_FILENAME="$(basename "$CHECKPOINT_PATH")"', ENTRYPOINT)
        self.assertIn('CHECKPOINT_PATH="$FALLBACK_DIR/$CHECKPOINT_FILENAME"', ENTRYPOINT)

    def test_kaggle_listing_download_and_extraction_use_selected_filename(self):
        self.assertIn('grep -Fq "$CHECKPOINT_FILENAME" "$TEMP_DIR/files.log"', ENTRYPOINT)
        self.assertIn('-f "$CHECKPOINT_FILENAME"', ENTRYPOINT)
        self.assertIn('-name "$CHECKPOINT_FILENAME"', ENTRYPOINT)


if __name__ == "__main__":
    unittest.main()
