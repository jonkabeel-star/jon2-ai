"""Regression tests for conservative Jon2 auto-repair rules."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.jon2_auto_repair import (
    analyze_incident_log, diagnose_failure, generate_safe_repairs, normalize_python_whitespace,
    restore_snapshot, snapshot_repair_scope, should_discover_repository_repairs,
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

    def test_untrusted_issue_report_is_diagnostic_only(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        original = "def run():\n    return json.dumps({})\n"
        target.write_text(original, encoding="utf-8")
        diagnostics, proposals = analyze_incident_log(self.root, self._log(target), allow_repairs=False)
        self.assertTrue(diagnostics)
        self.assertEqual(proposals[0]["status"], "diagnostic_only")
        self.assertEqual(target.read_text(encoding="utf-8"), original)

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

    def test_discovers_known_errors_from_failed_check_output(self) -> None:
        from scripts.jon2_auto_repair import analyze_failed_checks

        checks = [
            {"name": "unit_tests", "passed": False, "output": "ModuleNotFoundError: No module named yaml"},
            {"name": "compile", "passed": True, "output": "NameError: should_not_be_scanned"},
        ]
        failure_text, findings = analyze_failed_checks(checks)
        self.assertIn("ModuleNotFoundError", failure_text)
        self.assertNotIn("should_not_be_scanned", failure_text)
        self.assertEqual(findings[0]["category"], "missing_dependency")
        self.assertEqual(findings[0]["action"], "diagnostic_only")

    def test_failed_validation_can_restore_original_source_bytes(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        original = b"def run():  \n    return 1\n"
        target.write_bytes(original)
        snapshot = snapshot_repair_scope(self.root)
        target.write_text("import json\ndef run():\n    return 1\n", encoding="utf-8")
        restored = restore_snapshot(snapshot)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(restored, [str(target)])

    def test_snapshot_never_follows_symlinks_outside_scope(self) -> None:
        target = self.root / "ai_engine" / "real.py"
        outside = self.root.parent / (self.root.name + "-outside.py")
        link = self.root / "ai_engine" / "linked.py"
        try:
            target.write_text("value = 1\\n", encoding="utf-8")
            outside.write_text("outside = 1\\n", encoding="utf-8")
            link.symlink_to(outside)
            snapshot = snapshot_repair_scope(self.root)
            self.assertIn(target.resolve(), snapshot)
            self.assertNotIn(outside.resolve(), snapshot)
        finally:
            if outside.exists():
                outside.unlink()

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

    def test_external_or_diagnostic_incidents_never_trigger_repository_repairs(self) -> None:
        self.assertFalse(should_discover_repository_repairs(incident_log_supplied=True, diagnostic_only=False))
        self.assertFalse(should_discover_repository_repairs(incident_log_supplied=True, diagnostic_only=True))
        self.assertFalse(should_discover_repository_repairs(incident_log_supplied=False, diagnostic_only=True))
        self.assertTrue(should_discover_repository_repairs(incident_log_supplied=False, diagnostic_only=False))

    def test_diagnostic_only_mode_does_not_normalize_source_files(self) -> None:
        target = self.root / "ai_engine" / "sample.py"
        original = b"def run():  \n    return 1\n"
        target.write_bytes(original)
        changed = normalize_python_whitespace(self.root, enabled=False)
        self.assertEqual(changed, [])
        self.assertEqual(target.read_bytes(), original)

    def test_whitespace_normalizer_never_follows_symlinks_outside_scope(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.py")
        original = b"x = 1  \n"
        try:
            outside.write_bytes(original)
            link = self.root / "ai_engine" / "linked.py"
            link.symlink_to(outside)
            changed = normalize_python_whitespace(self.root)
            self.assertEqual(changed, [])
            self.assertEqual(outside.read_bytes(), original)
        finally:
            if outside.exists():
                outside.unlink()


if __name__ == "__main__":
    unittest.main()
