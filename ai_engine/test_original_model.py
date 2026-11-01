"""Tests for the original Jon2 tokenizer and causal Transformer.

These tests verify architecture and serialization only. They do not claim that
randomly initialized weights constitute a trained conversational model.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from jon2_core import Jon2Transformer, load_model
from tokenizer import ByteBPETokenizer


class ByteBPETokenizerTests(unittest.TestCase):
    def test_arabic_latin_punctuation_and_emoji_round_trip(self):
        text = "مرحباً Jon2! 🌟\nكيف الحال؟"
        tokenizer = ByteBPETokenizer.train(text * 3, vocab_size=300)
        self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)

    def test_unseen_text_uses_utf8_byte_fallback(self):
        training_text = "هذه بيانات تدريب عربية."
        tokenizer = ByteBPETokenizer.train(training_text, vocab_size=280)
        unseen = "🪐 نص جديد"
        self.assertEqual(tokenizer.decode(tokenizer.encode(unseen)), unseen)

    def test_serialization_preserves_token_ids(self):
        text = "اختبار tokenizer 123"
        tokenizer = ByteBPETokenizer.train(text * 4, vocab_size=320)
        restored = ByteBPETokenizer.from_dict(tokenizer.to_dict())
        self.assertEqual(restored.encode(text), tokenizer.encode(text))
        self.assertEqual(restored.decode(restored.encode(text)), text)

    def test_rejects_invalid_merge_reference(self):
        with self.assertRaises(ValueError):
            ByteBPETokenizer.from_dict({
                "format": "jon2-byte-bpe-v1",
                "base_vocab_size": 256,
                "merges": [[256, 1]],
            })


class Jon2TransformerTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.model = Jon2Transformer(
            vocab_size=300,
            width=32,
            heads=4,
            layers=2,
            context=16,
            dropout=0.0,
        )
        self.model.eval()

    def test_forward_shape_and_finite_logits(self):
        tokens = torch.randint(0, 300, (2, 8))
        logits = self.model(tokens)
        self.assertEqual(tuple(logits.shape), (2, 8, 300))
        self.assertTrue(torch.isfinite(logits).all().item())

    def test_future_tokens_do_not_change_past_logits(self):
        first = torch.tensor([[1, 2, 3, 4, 5]])
        changed_future = torch.tensor([[1, 2, 3, 99, 100]])
        with torch.inference_mode():
            logits_a = self.model(first)
            logits_b = self.model(changed_future)
        self.assertTrue(torch.allclose(logits_a[:, :3], logits_b[:, :3], atol=1e-6))

    def test_context_window_keeps_last_tokens(self):
        tokens = torch.randint(0, 300, (1, 20))
        logits = self.model(tokens)
        self.assertEqual(tuple(logits.shape), (1, 16, 300))

    def test_checkpoint_round_trip_restores_model_and_tokenizer(self):
        text = "نص عربي للتجربة. " * 8
        tokenizer = ByteBPETokenizer.train(text, vocab_size=300)
        config = {
            "width": 32,
            "heads": 4,
            "layers": 2,
            "context": 16,
            "dropout": 0.0,
        }
        model = Jon2Transformer(vocab_size=tokenizer.vocab_size, **config)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint_path = Path(directory) / "jon2-test.pt"
            torch.save({
                "model_state": model.state_dict(),
                "tokenizer": tokenizer.to_dict(),
                "config": config,
                "training_steps": 12,
                "model_name": "Jon2 Original Transformer",
            }, checkpoint_path)
            restored, restored_tokenizer, device = load_model(
                str(checkpoint_path), device="cpu"
            )
            self.assertEqual(device.type, "cpu")
            self.assertEqual(restored_tokenizer.encode(text), tokenizer.encode(text))
            self.assertEqual(restored.training, False)
            self.assertEqual(
                set(restored.state_dict()),
                set(model.state_dict()),
            )


if __name__ == "__main__":
    unittest.main()
