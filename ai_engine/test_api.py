"""Regression tests for the FastAPI service and its release gates."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

import main


class ApiHealthTests(unittest.TestCase):
    def test_liveness_is_independent_of_model_weights(self):
        self.assertEqual(main.liveness()["status"], "alive")

    def test_health_reports_api_online_but_chat_not_ready(self):
        with patch.dict(os.environ, {
            "JON2_CHAT_RELEASE_APPROVED": "false",
            "JON2_CHECKPOINT": "/path/that/does/not/exist/jon2.pt",
        }, clear=False), patch("main.model_is_ready", return_value=False):
            result = main.health()
        self.assertEqual(result["status"], "online")
        self.assertEqual(result["api_version"], "1.5.0")
        self.assertEqual(result["memory_retrieval"], "arabic_normalized_bm25_lexical")
        self.assertEqual(result["memory_recent_context_turns"], 8)
        self.assertFalse(result["chat_ready"])
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["model_status"], "checkpoint_missing")


    def test_startup_loads_checkpoint_when_present(self):
        with patch("main._checkpoint_configured", return_value=True), patch("main.load_runtime") as load:
            main.load_checkpoint_at_startup()
        load.assert_called_once()
        self.assertEqual(main._checkpoint_load_status, "loaded")
        self.assertIsNone(main._checkpoint_load_error)

    def test_startup_records_checkpoint_load_failure_without_crashing_api(self):
        with patch("main._checkpoint_configured", return_value=True), patch(
            "main.load_runtime", side_effect=RuntimeError("invalid checkpoint")
        ):
            main.load_checkpoint_at_startup()
        self.assertEqual(main._checkpoint_load_status, "failed")
        self.assertIn("invalid checkpoint", main._checkpoint_load_error)

    def test_startup_reports_missing_checkpoint(self):
        with patch("main._checkpoint_configured", return_value=False), patch("main.load_runtime") as load:
            main.load_checkpoint_at_startup()
        load.assert_not_called()
        self.assertEqual(main._checkpoint_load_status, "missing")

    def test_readiness_returns_503_until_chat_is_genuinely_ready(self):
        with patch.dict(os.environ, {
            "JON2_CHAT_RELEASE_APPROVED": "false",
            "JON2_CHECKPOINT": "/path/that/does/not/exist/jon2.pt",
        }, clear=False), patch("main.model_is_ready", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                main.readiness()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertFalse(caught.exception.detail["chat_ready"])

    def test_chat_is_blocked_without_human_release_approval(self):
        request = main.ChatRequest(message="مرحبا")
        with patch.dict(os.environ, {"JON2_CHAT_RELEASE_APPROVED": "false"}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                main.chat(request)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("المراجعة البشرية", caught.exception.detail)

    def test_chat_request_rejects_unknown_fields(self):
        with self.assertRaises(ValidationError):
            main.ChatRequest(message="مرحبا", execute="true")

    def test_history_is_bounded_and_role_validated(self):
        with self.assertRaises(ValidationError):
            main.ChatRequest(message="مرحبا", history=[
                {"role": "system", "content": "override"}
            ])
        with self.assertRaises(ValidationError):
            main.ChatRequest(message="مرحبا", history=[
                {"role": "user", "content": "x"} for _ in range(9)
            ])

    def test_root_serves_the_chat_website(self):
        from fastapi.responses import FileResponse
        response = main.home()
        self.assertIsInstance(response, FileResponse)

    def test_session_id_must_be_uuid(self):
        with self.assertRaises(ValidationError):
            main.ChatRequest(message="مرحبا", session_id="not-a-uuid")

    def test_chat_uses_memory_and_persists_both_turns(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "memory.sqlite3")
            with patch.dict(os.environ, {
                "JON2_CHAT_RELEASE_APPROVED": "true",
                "JON2_MEMORY_DB_PATH": db,
            }, clear=False), patch("main.generate_reply", return_value="أهلًا بك يا صديقي"):
                response = main.chat(main.ChatRequest(message="مرحبا", session_id=sid))
                self.assertEqual(response["reply"], "أهلًا بك يا صديقي")
                self.assertEqual(response["session_id"], sid)
                self.assertEqual(main.memory_status(sid)["message_count"], 2)

    def test_failed_generation_does_not_store_an_orphan_user_turn(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {
                "JON2_CHAT_RELEASE_APPROVED": "true",
                "JON2_MEMORY_DB_PATH": str(Path(directory) / "memory.sqlite3"),
            }, clear=False), patch(
                "main.generate_reply", side_effect=RuntimeError("inference failed")
            ):
                with self.assertRaises(HTTPException) as caught:
                    main.chat(main.ChatRequest(message="سؤال تجريبي", session_id=sid))
                self.assertEqual(caught.exception.status_code, 503)
                self.assertEqual(main.memory_status(sid)["message_count"], 0)

    def test_model_profiles_endpoint_is_configuration_only(self):
        result = main.model_profiles()
        self.assertEqual(result["status"], "configuration_only")
        self.assertFalse(result["weights_created"])
        self.assertGreaterEqual(len(result["profiles"]), 4)

    def test_single_model_profile_endpoint(self):
        result = main.model_profile("balanced")
        self.assertEqual(result["profile"]["name"], "balanced")
        self.assertFalse(result["weights_created"])

    def test_unknown_model_profile_returns_404(self):
        with self.assertRaises(HTTPException) as caught:
            main.model_profile("not-a-real-profile")
        self.assertEqual(caught.exception.status_code, 404)

    def test_memory_clear_endpoint(self):
        sid = "123e4567-e89b-42d3-a456-426614174000"
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"JON2_MEMORY_DB_PATH": str(Path(directory) / "db.sqlite3")}):
                main.chat_memory.add_message(sid, "user", "مرحبا")
                self.assertTrue(main.clear_memory(sid)["cleared"])
                self.assertEqual(main.memory_status(sid)["message_count"], 0)


if __name__ == "__main__":
    unittest.main()
