"""API validation tests for worker metadata."""
import unittest
from pydantic import ValidationError

from compute.worker_routes import EnrollmentRequest, HeartbeatRequest


class WorkerRouteValidationTests(unittest.TestCase):
    def test_enrollment_rejects_delimiter_in_accelerator_metadata(self):
        with self.assertRaises(ValidationError):
            EnrollmentRequest(
                node_id="node-001", platform="linux", cpu_count=2,
                memory_total_bytes=1024, accelerator_types=["cuda,gpu"],
            )

    def test_heartbeat_rejects_control_characters(self):
        with self.assertRaises(ValidationError):
            HeartbeatRequest(
                cpu_count=2, memory_total_bytes=1024,
                accelerator_names=["GPU\nInjected"],
            )

    def test_valid_metadata_is_accepted(self):
        request = HeartbeatRequest(
            cpu_count=4, memory_total_bytes=4096,
            accelerator_types=["cuda"], accelerator_names=["NVIDIA GPU"],
        )
        self.assertEqual(request.accelerator_types, ["cuda"])


if __name__ == "__main__":
    unittest.main()
