"""Tests for the read-only Jon2 engineering agent."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engineer_agent import build_engineering_plan, inspect_language_engine


class EngineeringAgentTests(unittest.TestCase):
    def test_inspects_python_without_importing_model_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "language_engine.py"
            path.write_text("class Engine:\n    def load_model(self): pass\n    def generate(self): pass\n", encoding="utf-8")
            result = inspect_language_engine(path)
        self.assertTrue(result["syntax_valid"])
        self.assertTrue(result["has_model_loader"])
        self.assertTrue(result["has_generation_entrypoint"])
        self.assertFalse(result["has_evaluation_hook"])

    def test_plan_does_not_claim_model_evaluation_or_training(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ai_engine").mkdir()
            (root / "ai_engine" / "language_engine.py").write_text(
                "class Engine:\n    def load_model(self): pass\n    def generate(self): pass\n",
                encoding="utf-8",
            )
            cases = root / "cases.jsonl"
            cases.write_text(
                '{"test_id":"a","dialect":"egyptian","prompt":"سؤال","expected_terms":["جواب"],"forbidden_terms":[]}\n',
                encoding="utf-8",
            )
            report = build_engineering_plan(root, cases)
        self.assertFalse(report["benchmark"]["model_answers_evaluated"])
        self.assertFalse(report["code_changes_made"])
        self.assertFalse(report["training_started"])
        self.assertTrue(any(task["area"] == "code_generation" for task in report["tasks"]))


if __name__ == "__main__":
    unittest.main()
