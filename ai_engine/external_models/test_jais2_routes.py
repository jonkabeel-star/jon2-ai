import os
import sys
import unittest
from pathlib import Path

# Match the server's execution layout, where ai_engine is the import root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch

from fastapi import HTTPException

from jais2_routes import ArabicChatRequest, jais2_chat, jais2_health


class Jon2ArabicRouteTests(unittest.TestCase):
    def tearDown(self):
        for key in ("JON2_JAIS2_API_ENABLED", "JON2_JAIS2_API_TOKEN"):
            os.environ.pop(key, None)

    def test_health_is_disabled_by_default(self):
        os.environ.pop("JON2_JAIS2_API_ENABLED", None)
        self.assertEqual(jais2_health()["status"], "disabled")

    def test_chat_rejects_when_disabled(self):
        with self.assertRaises(HTTPException) as ctx:
            jais2_chat(ArabicChatRequest(message="عامل إيه؟"), None)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_chat_requires_configured_token(self):
        os.environ["JON2_JAIS2_API_ENABLED"] = "true"
        with self.assertRaises(HTTPException) as ctx:
            jais2_chat(ArabicChatRequest(message="عامل إيه؟"), "Bearer x")
        self.assertEqual(ctx.exception.status_code, 503)

    def test_chat_rejects_wrong_token(self):
        os.environ["JON2_JAIS2_API_ENABLED"] = "true"
        os.environ["JON2_JAIS2_API_TOKEN"] = "private-test-token"
        with self.assertRaises(HTTPException) as ctx:
            jais2_chat(ArabicChatRequest(message="عامل إيه؟"), "Bearer wrong")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_chat_uses_local_runtime_after_authorization(self):
        os.environ["JON2_JAIS2_API_ENABLED"] = "true"
        os.environ["JON2_JAIS2_API_TOKEN"] = "private-test-token"
        from unittest.mock import patch
        with patch("external_models.jais2_runtime.generate_reply", return_value="تمام، الحمد لله.") as generate:
            result = jais2_chat(
                ArabicChatRequest(message="عامل إيه؟"),
                "Bearer private-test-token",
            )
        self.assertEqual(result["reply"], "تمام، الحمد لله.")
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
