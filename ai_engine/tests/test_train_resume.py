"""Regression tests for safe continuation of Jon2 training."""
import sys
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from train_jon2 import resume_plan_differences


class ResumePlanTests(unittest.TestCase):
    def setUp(self):
        self.saved = {
            "steps": 1200,
            "batch_size": 4,
            "context": 256,
            "width": 128,
            "heads": 4,
            "layers": 4,
            "learning_rate": 0.0003,
            "tokenizer_vocab_size": 1024,
            "validation_split_algorithm": "seeded_paragraph_blocks_v1",
        }

    def test_allows_only_total_step_target_to_increase(self):
        continued = dict(self.saved, steps=2400)
        self.assertEqual(resume_plan_differences(self.saved, continued), {})

    def test_rejects_learning_rate_change(self):
        continued = dict(self.saved, steps=2400, learning_rate=0.0001)
        differences = resume_plan_differences(self.saved, continued)
        self.assertIn("learning_rate", differences)
        self.assertEqual(differences["learning_rate"]["saved"], 0.0003)
        self.assertEqual(differences["learning_rate"]["current"], 0.0001)

    def test_rejects_tokenizer_vocabulary_change(self):
        continued = dict(self.saved, steps=2400, tokenizer_vocab_size=2048)
        self.assertIn(
            "tokenizer_vocab_size",
            resume_plan_differences(self.saved, continued),
        )

    def test_rejects_missing_training_setting(self):
        continued = dict(self.saved, steps=2400)
        del continued["context"]
        differences = resume_plan_differences(self.saved, continued)
        self.assertIn("context", differences)
        self.assertEqual(differences["context"]["current"], "<missing>")

    def test_legacy_checkpoint_without_plan_remains_identifiable(self):
        self.assertEqual(resume_plan_differences(None, self.saved), {})


if __name__ == "__main__":
    unittest.main()
