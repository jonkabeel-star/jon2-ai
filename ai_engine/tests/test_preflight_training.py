"""Tests for the read-only Jon2 training preflight gate."""
import sys
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from preflight_training import assess_readiness


class TrainingPreflightTests(unittest.TestCase):
    def base(self):
        return dict(
            corpus_characters=500_000,
            train_tokens=160_000_000,
            validation_tokens=40_000_000,
            parameter_count=20_000_000,
            tokenizer_vocab=8192,
            target_tokenizer_vocab=8192,
            context=1024,
            minimum_characters=100_000,
            minimum_tokens_per_parameter=10.0,
        )

    def test_accepts_ready_configuration(self):
        result = assess_readiness(**self.base())
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_blocks_small_corpus(self):
        args = self.base()
        args["corpus_characters"] = 99_999
        self.assertIn("corpus_below_minimum_characters",
                      assess_readiness(**args)["blockers"])

    def test_blocks_insufficient_tokens_per_parameter(self):
        args = self.base()
        args["train_tokens"] = 10_000
        args["validation_tokens"] = 2_000
        self.assertIn("insufficient_tokens_per_parameter",
                      assess_readiness(**args)["blockers"])

    def test_blocks_tokenizer_vocab_shortfall(self):
        args = self.base()
        args["tokenizer_vocab"] = 4096
        self.assertIn("tokenizer_did_not_reach_profile_vocabulary",
                      assess_readiness(**args)["blockers"])

    def test_blocks_short_train_and_validation_partitions(self):
        args = self.base()
        args["train_tokens"] = 100
        args["validation_tokens"] = 100
        blockers = assess_readiness(**args)["blockers"]
        self.assertIn("training_partition_too_short_for_context", blockers)
        self.assertIn("validation_partition_too_short_for_context", blockers)

    def test_reports_actual_parameter_count_not_profile_label(self):
        args = self.base()
        args["parameter_count"] = 19_000_000
        result = assess_readiness(**args)
        self.assertEqual(result["parameter_count_actual"], 19_000_000)
        self.assertAlmostEqual(result["tokens_per_parameter"], 200_000_000 / 19_000_000, places=5)


if __name__ == "__main__":
    unittest.main()
