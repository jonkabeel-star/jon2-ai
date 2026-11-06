import unittest

from large_model_preflight import (
    TARGET_PARAMETERS,
    build_report,
    estimate_adam_training_gib,
    estimate_storage_gib,
)


class LargeModelPreflightTests(unittest.TestCase):
    def test_twenty_billion_parameter_storage_estimates(self):
        report = build_report()
        self.assertEqual(report["target_parameters"], 20_000_000_000)
        self.assertAlmostEqual(report["weights_only_gib"]["bf16_fp16"], 37.25, places=1)
        self.assertAlmostEqual(report["weights_only_gib"]["fp32"], 74.5, places=1)
        self.assertAlmostEqual(
            report["full_parameter_adam_state_gib_excluding_activations"],
            335.28,
            places=1,
        )

    def test_adam_estimate_is_eighteen_bytes_per_parameter(self):
        self.assertAlmostEqual(
            estimate_adam_training_gib(1_000_000_000),
            18_000_000_000 / (1024 ** 3),
        )

    def test_rejects_invalid_parameter_counts(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                estimate_storage_gib(value, 2)

    def test_rejects_invalid_storage_width(self):
        for value in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                estimate_storage_gib(TARGET_PARAMETERS, value)

    def test_report_never_claims_weights_exist(self):
        self.assertEqual(
            build_report()["status"],
            "estimate_only_no_weights_or_training_created",
        )


if __name__ == "__main__":
    unittest.main()
