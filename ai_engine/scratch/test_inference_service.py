"""Tests the inference API's honest not-ready behavior without a checkpoint."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import serve_jon2


class InferenceServiceTests(unittest.TestCase):
    def setUp(self):
        serve_jon2._model = None
        serve_jon2._tokenizer = None
        serve_jon2._device = None
        serve_jon2._load_error = None
        self.client = TestClient(serve_jon2.app)

    def test_health_reports_missing_checkpoint(self):
        with patch.object(serve_jon2.CHECKPOINT, "is_file", return_value=False):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertFalse(response.json()["checkpoint_configured"])

    def test_chat_does_not_fake_a_reply_without_checkpoint(self):
        with patch.object(serve_jon2.CHECKPOINT, "is_file", return_value=False):
            response = self.client.post("/chat", json={"message": "مرحبا"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("غير متوفر", response.json()["detail"])

    def test_empty_message_is_rejected(self):
        response = self.client.post("/chat", json={"message": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
