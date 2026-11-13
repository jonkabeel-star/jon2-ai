"""Foundation regression tests for the original Jon2 Transformer.

These tests protect architecture semantics before any capacity or training changes.
They do not claim that a passing model is a capable Arabic assistant.
"""
import sys
import unittest
from pathlib import Path

import torch

AI_ENGINE = Path(__file__).resolve().parent
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from jon2_core import Jon2Transformer
from model_profiles import estimate_parameters
from tokenizer import ByteBPETokenizer


class Jon2ArchitectureBaselineTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)
        self.model = Jon2Transformer(
            vocab_size=320,
            width=32,
            heads=4,
            layers=2,
            context=16,
            dropout=0.0,
        ).eval()

    def test_forward_returns_next_token_logits_with_expected_shape(self):
        token_ids = torch.randint(0, 320, (2, 9), dtype=torch.long)
        logits = self.model(token_ids)
        self.assertEqual(tuple(logits.shape), (2, 9, 320))
        self.assertTrue(torch.isfinite(logits).all())

    def test_causal_attention_does_not_leak_future_tokens(self):
        original = torch.tensor([[3, 7, 11, 13, 17, 19, 23, 29]], dtype=torch.long)
        changed_future = original.clone()
        changed_future[:, 4:] = torch.tensor([[31, 37, 41, 43]], dtype=torch.long)

        with torch.inference_mode():
            before = self.model(original)
            after = self.model(changed_future)

        # Logits through position 3 may only depend on positions 0..3.
        torch.testing.assert_close(before[:, :4, :], after[:, :4, :], rtol=0, atol=1e-6)

    def test_batch_items_are_independent(self):
        first = torch.tensor([[2, 4, 6, 8]], dtype=torch.long)
        second = torch.tensor([[10, 12, 14, 16]], dtype=torch.long)
        combined = torch.cat((first, second), dim=0)
        with torch.inference_mode():
            separate_logits = self.model(first)
            combined_logits = self.model(combined)
        # Batched and single-item CPU kernels may accumulate floating-point
        # operations in a different order. Keep a tight absolute bound while
        # allowing normal FP32 round-off; this still detects real cross-item leakage.
        torch.testing.assert_close(
            separate_logits[0], combined_logits[0], rtol=0, atol=5e-6
        )

    def test_inputs_longer_than_context_are_safely_truncated(self):
        token_ids = torch.randint(0, 320, (1, 21), dtype=torch.long)
        logits = self.model(token_ids)
        self.assertEqual(tuple(logits.shape), (1, 16, 320))

    def test_input_and_output_embeddings_are_weight_tied(self):
        self.assertIs(
            self.model.token_embedding.weight,
            self.model.output.weight,
        )

    def test_parameter_estimate_matches_real_model(self):
        expected = estimate_parameters(
            width=32, layers=2, context=16, vocab_size=320
        )
        actual = sum(parameter.numel() for parameter in self.model.parameters())
        self.assertEqual(actual, expected)

    def test_arabic_bpe_round_trip_is_exact(self):
        training_text = "هذا نص عربي لتدريب Jon2. " * 12
        tokenizer = ByteBPETokenizer.train(training_text, vocab_size=320)
        sample = "أهلًا! دي تجربة عربية لـ Jon2 — ١٢٣ 😊"
        self.assertEqual(tokenizer.decode(tokenizer.encode(sample)), sample)


if __name__ == "__main__":
    unittest.main()
