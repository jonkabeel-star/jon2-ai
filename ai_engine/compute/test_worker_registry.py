import os
import tempfile
import unittest
from unittest.mock import patch

from compute import worker_registry as registry


class WorkerRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.temp.name, "workers.sqlite3")
        self.env = patch.dict(os.environ, {
            "JON2_COMPUTE_DB_PATH": self.db,
            "JON2_COMPUTE_OWNER_TOKEN": "x" * 48,
        })
        self.env.start()
        registry.initialize()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_enroll_heartbeat_and_list_without_exposing_secret(self):
        token = registry.enroll(
            node_id="test-node-001", display_name="Test Node",
            platform="linux", cpu_count=4, memory_total_bytes=8 * 1024**3,
            accelerator_types=["cuda"], accelerator_names=["Test GPU"]
        )
        self.assertTrue(registry.authenticate_worker("test-node-001", token))
        self.assertTrue(registry.heartbeat(
            "test-node-001", token, 6, 12 * 1024**3, ["cuda"], ["Test GPU"]
        ))
        item = registry.list_workers()[0]
        self.assertEqual(item["status"], "online")
        self.assertEqual(item["cpu_count"], 6)
        self.assertNotIn("token", item)
        self.assertNotIn(token, str(item))

    def test_bad_token_and_revocation(self):
        token = registry.enroll(
            node_id="test-node-002", display_name="Node",
            platform="linux", cpu_count=2, memory_total_bytes=1024,
            accelerator_types=[], accelerator_names=[]
        )
        self.assertFalse(registry.authenticate_worker("test-node-002", "wrong"))
        self.assertTrue(registry.revoke("test-node-002"))
        self.assertFalse(registry.authenticate_worker("test-node-002", token))
        self.assertEqual(registry.list_workers()[0]["status"], "stale_or_revoked")

    def test_owner_token_requires_32_characters(self):
        with patch.dict(os.environ, {"JON2_COMPUTE_OWNER_TOKEN": "short"}):
            self.assertFalse(registry.owner_token_configured())
            self.assertFalse(registry.verify_owner_token("short"))


if __name__ == "__main__":
    unittest.main()
