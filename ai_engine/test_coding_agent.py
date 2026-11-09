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
        raw = "```diff\\n" + VALID + "```\\nNO_SAFE_PATCH"
        self.assertEqual(extract_patch(raw), VALID.strip())

    def test_extracts_plain_diff_after_preamble(self):
        self.assertEqual(extract_patch("Here is the patch:\\n" + VALID), VALID.strip())

    def test_no_safe_patch_is_preserved(self):
        self.assertEqual(extract_patch("NO_SAFE_PATCH"), "NO_SAFE_PATCH")

    def test_rejects_out_of_scope_patch(self):
        patch = VALID.replace("ai_engine/example.py", "ai_engine/training_gate.py")
        with self.assertRaises(PermissionError):
            validate(patch)

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
