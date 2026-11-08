import unittest

from model_profiles import PROFILES, describe_profile, estimate_parameters, list_profiles


class ModelProfileTests(unittest.TestCase):
    def test_profiles_are_ordered_by_capacity(self):
        counts = [item["estimated_parameters"] for item in list_profiles()]
        self.assertEqual(counts, sorted(counts))
        self.assertEqual(len(counts), len(PROFILES))

    def test_profile_reports_configuration_not_weights(self):
        result = describe_profile("advanced")
        self.assertGreater(result["estimated_parameters"], 1_000_000)
        self.assertEqual(result["training_status"], "configuration_only_no_weights_created")
        self.assertEqual(result["width"], 256)
        self.assertEqual(result["heads"], 8)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            describe_profile("8b_magic")

    def test_dimensions_must_be_positive_integers(self):
        with self.assertRaises(ValueError):
            estimate_parameters(width=0, layers=2, context=32, vocab_size=256)
        with self.assertRaises(ValueError):
            estimate_parameters(width=True, layers=2, context=32, vocab_size=256)

    def test_profiles_have_valid_attention_dimensions(self):
        for profile in PROFILES.values():
            self.assertEqual(profile.width % profile.heads, 0)


if __name__ == "__main__":
    unittest.main()
