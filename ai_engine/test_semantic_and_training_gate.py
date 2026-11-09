"""Fail-closed tests for semantic judging and training authorization."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from semantic_evaluator import judge_answer
from training_gate import main, prepare


class SemanticAndTrainingTests(unittest.TestCase):
    def test_semantic_judge_accepts_only_strict_positive_json(self):
        data = {
            "semantically_correct": True,
            "answers_question": True,
            "contains_material_error": False,
            "contains_unsupported_claim": False,
            "dialect_appropriate": True,
            "confidence": 0.91,
            "rationale": "صحيح",
            "issues": [],
        }
        with patch("semantic_evaluator._chat", return_value=json.dumps(data)):
            result = judge_answer(
                {"test_id": "x", "reference_answer": "مرجع", "prompt": "سؤال"},
                "جواب",
            )
        self.assertTrue(result["passed"])

    def test_semantic_judge_rejects_wrong_answer(self):
        data = {
            "semantically_correct": False,
            "answers_question": True,
            "contains_material_error": True,
            "contains_unsupported_claim": False,
            "dialect_appropriate": True,
            "confidence": 0.99,
            "rationale": "خطأ",
            "issues": ["خطأ"],
        }
        with patch("semantic_evaluator._chat", return_value=json.dumps(data)):
            result = judge_answer(
                {"test_id": "x", "reference_answer": "مرجع"}, "خاطئ"
            )
        self.assertFalse(result["passed"])

    def test_semantic_judge_requires_reference(self):
        with self.assertRaises(ValueError):
            judge_answer({"test_id": "x"}, "جواب")

    def test_training_never_authorizes_when_preflight_blocked(self):
        fake = {
            "readiness": {
                "ready": False,
                "blockers": ["insufficient_tokens_per_parameter"],
            }
        }
        with (
            patch("training_gate.build_report", return_value=fake),
            patch("torch.cuda.is_available", return_value=False),
        ):
            result = prepare(
                Path("."),
                Path("approvals.json"),
                "arabic_30m",
                Path("not-created.pt"),
            )
        self.assertFalse(result["authorized_to_train"])
        self.assertFalse(result["training_started"])

    def test_authorized_dry_run_does_not_launch_trainer(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "gate.json"
            authorized = {
                "authorized_to_train": True,
                "training_started": False,
                "training_completed": False,
            }
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "training_gate.py",
                        "--checkpoint",
                        str(Path(directory) / "new.pt"),
                        "--report",
                        str(report),
                    ],
                ),
                patch("training_gate.prepare", return_value=authorized),
                patch("training_gate.subprocess.run") as run,
            ):
                self.assertEqual(main(), 0)
            run.assert_not_called()
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(saved["authorized_to_train"])
            self.assertFalse(saved["training_completed"])

    def test_execute_returns_failure_when_trainer_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "gate.json"
            authorized = {
                "authorized_to_train": True,
                "training_started": False,
                "training_completed": False,
            }
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "training_gate.py",
                        "--execute",
                        "--checkpoint",
                        str(Path(directory) / "new.pt"),
                        "--report",
                        str(report),
                    ],
                ),
                patch("training_gate.prepare", return_value=authorized),
                patch(
                    "training_gate.subprocess.run",
                    return_value=SimpleNamespace(returncode=17),
                ) as run,
            ):
                self.assertEqual(main(), 17)
            run.assert_called_once()
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(saved["trainer_invoked"])
            self.assertEqual(saved["trainer_exit_code"], 17)
            self.assertFalse(saved["training_started"])
            self.assertFalse(saved["training_completed"])

    def test_execute_reports_launch_error_as_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "gate.json"
            authorized = {
                "authorized_to_train": True,
                "training_started": False,
                "training_completed": False,
            }
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "training_gate.py",
                        "--execute",
                        "--checkpoint",
                        str(Path(directory) / "new.pt"),
                        "--report",
                        str(report),
                    ],
                ),
                patch("training_gate.prepare", return_value=authorized),
                patch(
                    "training_gate.subprocess.run",
                    side_effect=OSError("process unavailable"),
                ),
            ):
                self.assertEqual(main(), 127)
            saved = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(saved["trainer_exit_code"], 127)
            self.assertFalse(saved["training_completed"])


if __name__ == "__main__":
    unittest.main()
