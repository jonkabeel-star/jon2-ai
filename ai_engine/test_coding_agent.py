import tempfile
import unittest
from pathlib import Path
from coding_agent import collect_context, extract_patch, validate

VALID = """diff --git a/ai_engine/example.py b/ai_engine/example.py
--- a/ai_engine/example.py
+++ b/ai_engine/example.py
@@ -1 +1 @@
-old = 1
+new = 2
"""

class CodingAgentTests(unittest.TestCase):
    def test_extracts_fenced_diff_and_discards_trailing_model_text(self):
        raw = "```diff\n" + VALID + "```\nNO_SAFE_PATCH"
        self.assertEqual(extract_patch(raw), VALID.strip())

    def test_extracts_plain_diff_after_preamble(self):
        self.assertEqual(extract_patch("Here is the patch:\n" + VALID), VALID.strip())

    def test_extracts_standard_unified_diff_without_git_headers(self):
        standard = "--- a/ai_engine/example.py\n+++ b/ai_engine/example.py\n@@ -1 +1 @@\n-old = 1\n+new = 2"
        self.assertEqual(extract_patch("Patch follows:\n" + standard), standard)
        self.assertEqual(validate(standard), ["ai_engine/example.py"])

    def test_standard_unified_diff_still_rejects_path_traversal(self):
        standard = "--- a/ai_engine/example.py\n+++ b/ai_engine/../../server/evil.py\n@@ -1 +1 @@\n-old = 1\n+new = 2"
        with self.assertRaises(PermissionError):
            validate(standard)

    def test_no_safe_patch_is_preserved(self):
        self.assertEqual(extract_patch("NO_SAFE_PATCH"), "NO_SAFE_PATCH")

    def test_rejects_out_of_scope_patch(self):
        patch = VALID.replace("ai_engine/example.py", "ai_engine/training_gate.py")
        with self.assertRaises(PermissionError):
            validate(patch)

    def test_rejects_parent_directory_traversal(self):
        patch = VALID.replace("ai_engine/example.py", "ai_engine/../../server/evil.py")
        with self.assertRaises(PermissionError):
            validate(patch)

    def test_rejects_absolute_paths(self):
        patch = VALID.replace("ai_engine/example.py", "/tmp/evil.py")
        with self.assertRaises(PermissionError):
            validate(patch)

    def test_rejects_non_python_source_files(self):
        patch = VALID.replace("ai_engine/example.py", "ai_engine/README.md")
        with self.assertRaises(PermissionError):
            validate(patch)

    def test_rejects_malformed_model_response_without_a_diff(self):
        response = extract_patch("I changed the code. Trust me.")
        self.assertNotEqual(response, "NO_SAFE_PATCH")
        with self.assertRaises(ValueError):
            validate(response)

    def test_retries_once_after_malformed_model_response(self):
        from unittest.mock import patch
        with patch("coding_agent._request_ollama_patch", side_effect=["not a diff", VALID.strip()]) as request:
            result = __import__("coding_agent").propose("fix a bug", "local-model", "http://localhost:11434", str(Path(__file__).resolve().parent.parent))
        self.assertEqual(result, VALID.strip())
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.args[4], "not a diff")

    def test_stops_retrying_when_model_declines_safe_patch(self):
        from unittest.mock import patch
        with patch("coding_agent._request_ollama_patch", return_value="NO_SAFE_PATCH") as request:
            result = __import__("coding_agent").propose("inspect", "local-model", "http://localhost:11434", str(Path(__file__).resolve().parent.parent))
        self.assertEqual(result, "NO_SAFE_PATCH")
        self.assertEqual(request.call_count, 1)

    def test_retry_count_is_bounded(self):
        from unittest.mock import patch
        with patch("coding_agent._request_ollama_patch", return_value="still malformed") as request:
            result = __import__("coding_agent").propose("inspect", "local-model", "http://localhost:11434", str(Path(__file__).resolve().parent.parent), max_attempts=2)
        self.assertEqual(result, "still malformed")
        self.assertEqual(request.call_count, 2)

    def test_rejects_diff_that_does_not_match_current_source(self):
        import subprocess
        from coding_agent import check_patch_applicability
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ai_engine").mkdir()
            (root / "ai_engine" / "example.py").write_text("different = 9\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            with self.assertRaisesRegex(ValueError, "does not apply cleanly"):
                check_patch_applicability(root, VALID)

    def test_accepts_diff_that_matches_current_source_without_modifying_it(self):
        import subprocess
        from coding_agent import check_patch_applicability
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ai_engine").mkdir()
            target = root / "ai_engine" / "example.py"
            target.write_text("old = 1\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "jon2-tests@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Jon2 Tests"], cwd=root, check=True)
            subprocess.run(["git", "add", "ai_engine/example.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            self.assertTrue(check_patch_applicability(root, VALID))
            self.assertEqual(target.read_text(encoding="utf-8"), "old = 1\n")

    def test_repair_loop_retries_after_failed_sandbox_then_passes(self):
        from unittest.mock import patch
        from coding_agent import repair_until_green
        with patch("coding_agent.propose", side_effect=[VALID.strip(), VALID.strip()]) as proposer, \
             patch("coding_agent.sandbox", side_effect=[
                 {"tests_passed": False, "test_exit_code": 1, "test_log": "AssertionError", "executed_inside_no_network_docker": True},
                 {"tests_passed": True, "test_exit_code": 0, "test_log": "OK", "executed_inside_no_network_docker": True}
             ]) as runner:
            result=repair_until_green("repair", "model", "host", ".", "image", max_rounds=2)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(proposer.call_count, 2)
        self.assertIn("AssertionError", proposer.call_args.args[0])
        self.assertEqual(runner.call_count, 2)

    def test_repair_loop_stops_when_no_patch_needed(self):
        from unittest.mock import patch
        from coding_agent import repair_until_green
        with patch("coding_agent.propose", return_value="NO_SAFE_PATCH") as proposer:
            result=repair_until_green("inspect", "model", "host", ".", "image")
        self.assertEqual(result["outcome"], "no_safe_patch_needed")
        self.assertTrue(result["passed"])
        proposer.assert_called_once()

    def test_repair_loop_fails_closed_after_bounded_failed_rounds(self):
        from unittest.mock import patch
        from coding_agent import repair_until_green
        with patch("coding_agent.propose", return_value=VALID.strip()) as proposer, \
             patch("coding_agent.sandbox", return_value={
                 "tests_passed": False, "test_exit_code": 1, "test_log": "still failing",
                 "executed_inside_no_network_docker": True
             }):
            result=repair_until_green("repair", "model", "host", ".", "image", max_rounds=2)
        self.assertFalse(result["passed"])
        self.assertEqual(result["outcome"], "repair_attempts_exhausted")
        self.assertEqual(proposer.call_count, 2)

    def test_context_contains_actual_engine_and_excludes_protected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ai_engine"
            root.mkdir()
            (root / "language_engine.py").write_text("class Jon2: pass", encoding="utf-8")
            (root / "training_gate.py").write_text("SECRET_TRAINING_CONTENT", encoding="utf-8")
            context = collect_context(tmp)
            self.assertIn("class Jon2: pass", context)
            self.assertNotIn("SECRET_TRAINING_CONTENT", context)

if __name__ == "__main__":
    unittest.main()
