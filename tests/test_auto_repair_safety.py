"""Regression tests for conservative Jon2 auto-repair rules."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.jon2_auto_repair import (
    diagnose_failure, generate_safe_repairs, restore_snapshot, snapshot_repair_scope,
)


class SafeRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "ai_engine").mkdir()
        (self.root / "tests").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _log(self, target: Path, symbol: str = "json") -> str:
        return (
            "Traceback (most recent call last):\n"
            f'  File "{target}", line 8, in run\n'
            f"NameError: name '{symbol}' is not defined\n"
        )

    def test_inserts_allowlisted_import_after_module_docstring(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        target.write_text('"""module docs"""\n\ndef run():\n    return json.dumps({})\n', encoding="utf-8")
        result = generate_safe_repairs(self.root, self._log(target))
        self.assertEqual(result[0]["status"], "patched")
        self.assertEqual(target.read_text(encoding="utf-8").splitlines()[1], "import json")

    def test_does_not_guess_ambiguous_datetime_import(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        original = "def run():\n    return datetime.now()\n"
        target.write_text(original, encoding="utf-8")
        result = generate_safe_repairs(self.root, self._log(target, "datetime"))
        self.assertEqual(result[0]["status"], "unsupported")
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_uses_traceback_associated_with_name_error_not_later_failure(self) -> None:
        first = self.root / "ai_engine" / "first.py"
        later = self.root / "ai_engine" / "later.py"
        first.write_text("def run():\n    return json.dumps({})\n", encoding="utf-8")
        later.write_text("def run():\n    return 1\n", encoding="utf-8")
        log = self._log(first) + (
            "Traceback (most recent call last):\n"
            f'  File "{later}", line 2, in run\n'
            "ValueError: later unrelated failure\n"
        )
        result = generate_safe_repairs(self.root, log)
        self.assertEqual(result[0]["status"], "patched")
        self.assertIn("import json", first.read_text(encoding="utf-8"))
        self.assertNotIn("import json", later.read_text(encoding="utf-8"))

    def test_refuses_path_outside_ai_engine(self) -> None:
        target = self.root / "tests" / "not_allowed.py"
        target.write_text("def run():\n    return json.dumps({})\n", encoding="utf-8")
        result = generate_safe_repairs(self.root, self._log(target))
        self.assertEqual(result[0]["status"], "unsupported")
        self.assertNotIn("import json", target.read_text(encoding="utf-8"))

    def test_does_not_duplicate_existing_import(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        target.write_text("import json\ndef run():\n    return json.dumps({})\n", encoding="utf-8")
        result = generate_safe_repairs(self.root, self._log(target))
        self.assertEqual(result[0]["status"], "already_imported")
        self.assertEqual(target.read_text(encoding="utf-8").count("import json"), 1)

    def test_classifies_dependency_path_and_function_failures_without_repair(self) -> None:
        log = (
            "ModuleNotFoundError: No module named yaml\n"
            "FileNotFoundError: [Errno 2] missing config.json\n"
            "TypeError: build() got an unexpected keyword argument mode\n"
        )
        findings = diagnose_failure(log)
        categories = {item["category"] for item in findings}
        self.assertEqual(categories, {"missing_dependency", "missing_path", "function_signature_mismatch"})
        self.assertTrue(all(item["action"] == "diagnostic_only" for item in findings))

    def test_failed_validation_can_restore_original_source_bytes(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        original = b"def run():  \n    return 1\n"
        target.write_bytes(original)
        snapshot = snapshot_repair_scope(self.root)
        target.write_text("import json\ndef run():\n    return 1\n", encoding="utf-8")
        restored = restore_snapshot(snapshot)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(restored, [str(target)])

    def test_snapshot_excludes_protected_model_and_training_paths(self) -> None:
        allowed = self.root / "ai_engine" / "sample.py"
        protected = self.root / "ai_engine" / "models" / "weights.py"
        protected.parent.mkdir()
        allowed.write_text("x = 1\n", encoding="utf-8")
        protected.write_text("secret = 1\n", encoding="utf-8")
        snapshot = snapshot_repair_scope(self.root)
        self.assertIn(allowed.resolve(), snapshot)
        self.assertNotIn(protected.resolve(), snapshot)

    def test_blocks_syntax_error_target(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        target.write_text("def broken(:\n", encoding="utf-8")
        result = generate_safe_repairs(self.root, self._log(target))
        self.assertEqual(result[0]["status"], "blocked")
        self.assertEqual(target.read_text(encoding="utf-8"), "def broken(:\n")


if __name__ == "__main__":
    unittest.main()
