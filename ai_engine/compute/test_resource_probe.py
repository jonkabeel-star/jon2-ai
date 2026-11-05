import unittest
from unittest.mock import patch

from ai_engine.compute.resource_probe import assess_task, inspect_resources


class ComputeProbeTests(unittest.TestCase):
    def test_snapshot_has_explicit_non_provisioned_status(self):
        snapshot = inspect_resources()
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertIn(snapshot["capacity_class"], {
            "cpu_only", "gpu_visible", "apple_mps_visible"
        })
        self.assertEqual(
            snapshot["provisioning_status"], "not_provisioned_by_this_service"
        )

    def test_gpu_required_is_rejected_without_cuda(self):
        with patch(
            "ai_engine.compute.resource_probe.inspect_resources",
            return_value={
                "memory": {"available_bytes": 8 * 1024 ** 3},
                "accelerators": [],
                "capacity_class": "cpu_only",
                "provisioning_status": "not_provisioned_by_this_service",
            },
        ):
            result = assess_task(min_memory_gib=2, require_gpu=True)
        self.assertFalse(result["accepted_for_execution"])
        self.assertFalse(result["execution_started"])
        self.assertFalse(result["gpu_visible"])

    def test_memory_requirement_must_be_positive(self):
        with self.assertRaises(ValueError):
            assess_task(min_memory_gib=0)


if __name__ == "__main__":
    unittest.main()
