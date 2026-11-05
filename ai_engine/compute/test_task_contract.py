"""Tests for the closed-by-default Jon2 Compute task contract."""
import unittest

from compute.task_contract import validate_task_request, validate_transition


class TaskContractTests(unittest.TestCase):
    def test_allowlisted_task_is_metadata_only_and_closed(self):
        task = validate_task_request(
            "task-001", "resource_probe", {"min_memory_gib": 1}
        )
        self.assertEqual(task["state"], "queued")
        self.assertFalse(task["dispatch_enabled"])

    def test_arbitrary_code_and_unknown_types_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_task_request("task-002", "shell", {"command": "whoami"})
        with self.assertRaises(ValueError):
            validate_task_request("task-003", "resource_probe", {"script": "print(1)"})

    def test_oversized_and_non_json_values_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_task_request("task-004", "health_check", {"data": "x" * 17000})
        with self.assertRaises(ValueError):
            validate_task_request("task-005", "health_check", {"bad": object()})

    def test_state_machine_blocks_skipping_and_terminal_reopen(self):
        validate_transition("queued", "assigned")
        validate_transition("assigned", "running")
        validate_transition("running", "succeeded")
        with self.assertRaises(ValueError):
            validate_transition("queued", "running")
        with self.assertRaises(ValueError):
            validate_transition("succeeded", "queued")


if __name__ == "__main__":
    unittest.main()
