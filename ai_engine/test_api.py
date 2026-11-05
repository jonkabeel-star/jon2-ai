"""Regression tests for the FastAPI service and its release gates."""
import os
import unittest
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
        self.assertEqual(result["api_version"], "1.2.0")
        self.assertFalse(result["chat_ready"])
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["model_status"], "checkpoint_missing")

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


if __name__ == "__main__":
    unittest.main()
