"""Tests for explicit training-use scope wiring in the Jon2 trainer CLI."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

import train_jon2


class TrainingUseScopeCliTests(unittest.TestCase):
    def run_main_and_capture_args(self, argv):
        with patch.object(train_jon2, "train") as mocked_train:
            with patch("sys.argv", ["train_jon2.py", *argv]):
                train_jon2.main()
        return mocked_train.call_args.args[0]

    def test_default_scope_is_private_research(self):
        args = self.run_main_and_capture_args([])
        self.assertEqual(args.required_intended_use, "research_training")

    def test_public_model_scope_is_explicit(self):
        args = self.run_main_and_capture_args(
            ["--required-intended-use", "public_model"]
        )
        self.assertEqual(args.required_intended_use, "public_model")

    def test_commercial_model_scope_is_explicit(self):
        args = self.run_main_and_capture_args(
            ["--required-intended-use", "commercial_model"]
        )
        self.assertEqual(args.required_intended_use, "commercial_model")

    def test_scope_is_recorded_in_resume_plan(self):
        args = self.run_main_and_capture_args([])
        plan = train_jon2._training_plan(args)
        self.assertEqual(plan["required_intended_use"], "research_training")

    def test_legacy_checkpoint_plan_defaults_to_research_only(self):
        current = {"required_intended_use": "research_training", "batch_size": 4}
        saved = {"batch_size": 4}
        self.assertEqual(
            train_jon2.resume_plan_differences(saved, current), {}
        )

    def test_legacy_checkpoint_cannot_resume_for_public_training(self):
        current = {"required_intended_use": "public_model", "batch_size": 4}
        saved = {"batch_size": 4}
        differences = train_jon2.resume_plan_differences(saved, current)
        self.assertIn("required_intended_use", differences)


if __name__ == "__main__":
    unittest.main()
