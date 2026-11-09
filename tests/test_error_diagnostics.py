"""Tests for structured Jon2 CI failure diagnostics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from jon2_error_diagnostics import analyze_failure_log


class ErrorDiagnosticsTests(unittest.TestCase):
    def test_classifies_common_python_errors_and_test_names(self):
        log = '''FAIL: test_chat_engine.test_reply
Traceback (most recent call last):
  File "ai_engine/chat_engine.py", line 42, in reply
TypeError: expected str, got None
'''
        result = analyze_failure_log(log)
        self.assertEqual(result["failed_tests"], ["test_chat_engine.test_reply"])
        self.assertEqual(result["diagnoses"][0]["category"], "type_error")
        self.assertEqual(result["diagnoses"][0]["file"], "ai_engine/chat_engine.py")
        self.assertEqual(result["diagnoses"][0]["line"], 42)

    def test_classifies_missing_dependency_without_editing(self):
        result = analyze_failure_log("ModuleNotFoundError: No module named 'fastapi'")
        self.assertEqual(result["diagnoses"][0]["category"], "module_not_found")
        self.assertFalse(result["automatic_repair_allowed"])
        self.assertFalse(result["log_content_executed"])

    def test_classifies_assertion_and_timeout(self):
        result = analyze_failure_log("AssertionError: expected Arabic response\nCHECK TIMED OUT")
        categories = {item["category"] for item in result["diagnoses"]}
        self.assertIn("assertion_failure", categories)
        self.assertIn("timeout", categories)

    def test_unrecognized_log_is_reported_without_guessing(self):
        result = analyze_failure_log("runner disconnected unexpectedly")
        self.assertEqual(result["diagnoses"], [])
        self.assertEqual(result["recognized_error_types"], 0)
        self.assertFalse(result["automatic_repair_allowed"])

    def test_bounds_failed_test_list(self):
        log = "\\n".join(f"FAIL: test_case_{i}" for i in range(75))
        result = analyze_failure_log(log)
        self.assertEqual(len(result["failed_tests"]), 50)


if __name__ == "__main__":
    unittest.main()
