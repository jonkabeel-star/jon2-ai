"""Capacity-profile tests for the from-scratch Jon2 Transformer."""
import sys
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from model_profiles import describe_profile, estimate_parameters


class Arabic30MProfileTests(unittest.TestCase):
    def test_arabic_30m_dimensions_and_parameter_count(self):
        profile = describe_profile("arabic_30m")
        self.assertEqual(profile["width"], 512)
        self.assertEqual(profile["heads"], 8)
        self.assertEqual(profile["layers"], 8)
        self.assertEqual(profile["context"], 1024)
        self.assertEqual(profile["tokenizer_vocab_size"], 8192)
        self.assertEqual(profile["estimated_parameters"], 29_938_688)
        self.assertEqual(
            profile["training_status"], "configuration_only_no_weights_created"
        )

    def test_larger_profile_is_materially_larger_than_cpu_small(self):
        small = describe_profile("cpu_small")
        large = describe_profile("arabic_30m")
        self.assertGreater(
            large["estimated_parameters"], small["estimated_parameters"] * 10
        )

    def test_parameter_estimator_rejects_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            estimate_parameters(width=0, layers=8, context=1024, vocab_size=8192)


if __name__ == "__main__":
    unittest.main()
