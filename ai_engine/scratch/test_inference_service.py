"""Tests the inference API's honest not-ready behavior without a checkpoint."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ENGINE_DIR = Path(__file__).resolve().parents[1]
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from fastapi.testclient import TestClient
import serve_jon2


class InferenceServiceTests(unittest.TestCase):
    def setUp(self):
        serve_jon2._model = None
        serve_jon2._tokenizer = None
        serve_jon2._device = None
        serve_jon2._load_error = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.missing_checkpoint = Path(self.temp_dir.name) / "missing-checkpoint.pt"
        self.checkpoint_patch = patch.object(
            serve_jon2, "CHECKPOINT", self.missing_checkpoint
        )
        self.checkpoint_patch.start()
        self.addCleanup(self.checkpoint_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.client = TestClient(serve_jon2.app)

    def test_health_reports_missing_checkpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertFalse(response.json()["checkpoint_configured"])

    def test_chat_does_not_fake_a_reply_without_checkpoint(self):
        response = self.client.post("/chat", json={"message": "مرحبا"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("غير متوفر", response.json()["detail"])

    def test_empty_message_is_rejected(self):
        response = self.client.post("/chat", json={"message": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
