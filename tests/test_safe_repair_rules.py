"""Regression tests for bounded path, symbol and dependency diagnostics."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from jon2_safe_repair_rules import (
    diagnose_dependency, suggest_path_repair, suggest_symbol_repair,
)


class SafeRepairRuleTests(unittest.TestCase):
    def test_unique_path_suggestion_is_bounded_and_non_mutating(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "ai_engine" / "config.py"
            target.parent.mkdir()
            target.write_text("VALUE = 1\n", encoding="utf-8")
            before = target.read_bytes()
            result = suggest_path_repair(root, "FileNotFoundError: config.py")
            self.assertEqual(result["status"], "suggestion")
            self.assertEqual(result["candidate"], "ai_engine/config.py")
            self.assertEqual(target.read_bytes(), before)
            outside = root / "private" / "config.py"
            outside.parent.mkdir()
            outside.write_text("SECRET = True\n", encoding="utf-8")
            self.assertEqual(suggest_path_repair(root, "FileNotFoundError: config.py")["status"], "suggestion")

    def test_ambiguous_paths_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in ("ai_engine", "tests"):
                (root / folder).mkdir()
                (root / folder / "same.py").write_text("pass\n", encoding="utf-8")
            result = suggest_path_repair(root, "No such file or directory: 'same.py'")
            self.assertEqual(result["status"], "ambiguous")
            self.assertEqual(len(result["candidates"]), 2)

    def test_symbol_suggestion_requires_real_ast_evidence_and_does_not_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "ai_engine"
            folder.mkdir()
            file = folder / "helpers.py"
            file.write_text("def calculate_total():\n    return 1\n", encoding="utf-8")
            before = file.read_bytes()
            result = suggest_symbol_repair(root, "AttributeError: object has no attribute 'calculate_totl'")
            self.assertEqual(result["status"], "suggestion")
            self.assertEqual(result["candidate"], "calculate_total")
            self.assertTrue(result["evidence_files"])
            self.assertTrue(result["requires_behavioral_test"])
            self.assertEqual(file.read_bytes(), before)

    def test_dependency_diagnosis_never_installs_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("fastapi>=0.1\n", encoding="utf-8")
            declared = diagnose_dependency(root, "ModuleNotFoundError: No module named 'fastapi'")
            unknown = diagnose_dependency(root, "ModuleNotFoundError: No module named 'made_up_pkg'")
            self.assertEqual(declared["status"], "declared_dependency_missing_at_runtime")
            self.assertEqual(unknown["status"], "undeclared_or_unmapped_dependency")
            self.assertFalse(declared["automatic_install"])
            self.assertFalse(unknown["installed_anything"])

    def test_stdlib_dependency_is_not_added_to_requirements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = diagnose_dependency(root, "ModuleNotFoundError: No module named 'json'")
            self.assertEqual(result["status"], "python_standard_library")
            self.assertFalse(result["installed_anything"])


if __name__ == "__main__":
    unittest.main()
