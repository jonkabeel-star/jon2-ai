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
