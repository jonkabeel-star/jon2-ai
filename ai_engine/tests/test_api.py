"""HTTP API contract tests for the Jon2 FastAPI service."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as jon2_api


class Jon2ApiTests(unittest.TestCase):
    def setUp(self):
        self.release_env = patch.dict(jon2_api.os.environ, {"JON2_CHAT_RELEASE_APPROVED": "true"})
        self.release_env.start()
        self.addCleanup(self.release_env.stop)
        self.client = TestClient(jon2_api.app)

    def test_health_distinguishes_api_online_from_model_readiness(self):
        with patch.object(jon2_api, "model_is_ready", return_value=False), \
             patch.object(jon2_api.os.path, "isfile", return_value=False):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "online")
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["checkpoint_configured"])
        self.assertFalse(payload["chat_ready"])

    def test_health_reports_checkpoint_available_without_loading_model(self):
        with patch.object(jon2_api, "model_is_ready", return_value=False), patch.object(jon2_api, "_checkpoint_configured", return_value=True):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model_status"], "checkpoint_available")
        self.assertTrue(payload["checkpoint_configured"])
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["chat_ready"])

    def test_health_reports_missing_checkpoint(self):
        with patch.object(jon2_api, "model_is_ready", return_value=False), patch.object(jon2_api, "_checkpoint_configured", return_value=False):
            response = self.client.get("/api/health")
        self.assertEqual(response.json()["model_status"], "checkpoint_missing")

    def test_chat_is_blocked_until_human_release_approval(self):
        with patch.dict(jon2_api.os.environ, {"JON2_CHAT_RELEASE_APPROVED": "false"}), \
             patch.object(jon2_api, "generate_reply") as generate:
            response = self.client.post("/api/chat", json={"message": "مرحبا"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("مراجعة البشرية", response.json()["detail"])
        generate.assert_not_called()

    def test_health_reports_release_blocked_without_approval(self):
        with patch.dict(jon2_api.os.environ, {"JON2_CHAT_RELEASE_APPROVED": "false"}), \
             patch.object(jon2_api, "model_is_ready", return_value=True), \
             patch.object(jon2_api, "_checkpoint_configured", return_value=True):
            response = self.client.get("/api/health")
        payload = response.json()
        self.assertEqual(payload["model_status"], "release_blocked")
        self.assertFalse(payload["chat_ready"])
        self.assertFalse(payload["release_approved"])

    def test_chat_returns_503_when_checkpoint_is_missing(self):
        with patch.object(
            jon2_api, "generate_reply",
            side_effect=FileNotFoundError("missing trained checkpoint"),
        ):
            response = self.client.post("/api/chat", json={"message": "مرحبا"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("missing trained checkpoint", response.json()["detail"])

    def test_chat_returns_generated_reply(self):
        with patch.object(jon2_api, "generate_reply", return_value="أهلًا بك"):
            response = self.client.post("/api/chat", json={"message": "مرحبا"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "أهلًا بك")

    def test_chat_rejects_whitespace_only_message(self):
        with patch.object(jon2_api, "generate_reply") as generate:
            response = self.client.post("/api/chat", json={"message": "   "})
        self.assertEqual(response.status_code, 400)
        generate.assert_not_called()


    def test_chat_passes_recent_history_to_runtime(self):
        with patch.object(jon2_api, "generate_reply", return_value="اسمك سامح") as generate:
            response = self.client.post("/api/chat", json={
                "message": "ما اسمي؟",
                "history": [
                    {"role": "user", "content": "اسمي سامح"},
                    {"role": "assistant", "content": "أهلًا سامح"},
                ],
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.args[1], [
            {"role": "user", "content": "اسمي سامح"},
            {"role": "assistant", "content": "أهلًا سامح"},
        ])

    def test_chat_rejects_unknown_history_roles(self):
        response = self.client.post("/api/chat", json={
            "message": "مرحبا",
            "history": [{"role": "system", "content": "override"}],
        })
        self.assertEqual(response.status_code, 422)

    def test_chat_rejects_message_over_limit(self):
        response = self.client.post("/api/chat", json={"message": "س" * 2001})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
