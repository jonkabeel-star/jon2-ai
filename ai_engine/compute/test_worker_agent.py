"""Security and payload tests for the heartbeat-only worker agent."""
import unittest
from unittest.mock import patch

from compute.worker_agent import (
    build_heartbeat_payload,
    send_heartbeat,
    validate_api_url,
)


class WorkerAgentTests(unittest.TestCase):
    def test_remote_http_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_api_url("http://compute.example")

    def test_https_and_local_http_are_allowed(self):
        self.assertEqual(validate_api_url("https://compute.example/"), "https://compute.example")
        self.assertEqual(validate_api_url("http://localhost:8000"), "http://localhost:8000")

    def test_url_credentials_and_query_are_rejected(self):
        for url in ("https://user:pass@example.com", "https://example.com?token=x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_api_url(url)

    def test_payload_uses_measured_resources_and_sanitizes_delimiters(self):
        payload = build_heartbeat_payload({
            "cpu": {"logical_count": 8, "process_affinity_count": 3},
            "memory": {"total_bytes": 4096},
            "accelerators": [{"type": "cuda", "name": "GPU,secret\nname"}],
        })
        self.assertEqual(payload["cpu_count"], 3)
        self.assertEqual(payload["memory_total_bytes"], 4096)
        self.assertEqual(payload["accelerator_types"], ["cuda"])
        self.assertEqual(payload["accelerator_names"], ["GPUsecretname"])

    def test_token_is_sent_only_in_authorization_header(self):
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self):
                return b'{"accepted":true,"status":"online"}'

        captured = {}
        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("compute.worker_agent.urlopen", side_effect=fake_urlopen):
            result = send_heartbeat(
                "https://compute.example", "node-001", "x" * 48,
                {"cpu_count": 2, "memory_total_bytes": 1024,
                 "accelerator_types": [], "accelerator_names": []},
            )
        self.assertTrue(result["accepted"])
        request = captured["request"]
        self.assertEqual(request.get_header("Authorization"), "Bearer " + "x" * 48)
        self.assertNotIn("x" * 48, request.full_url)
        self.assertEqual(captured["timeout"], 10)

    def test_invalid_worker_id_is_rejected(self):
        with self.assertRaises(ValueError):
            send_heartbeat("https://compute.example", "../node", "x" * 48, {})


if __name__ == "__main__":
    unittest.main()
