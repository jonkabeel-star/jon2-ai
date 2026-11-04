"""Tests that dialogue generation stops at the next user-turn marker."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jon2_core import generate
from tokenizer import ByteBPETokenizer


class ScriptedModel:
    context = 128

    def __init__(self, scripted_ids):
        self.scripted_ids = list(scripted_ids)
        self.calls = 0

    def __call__(self, tokens):
        logits = torch.full((1, tokens.shape[1], 256), -100.0)
        token_id = self.scripted_ids[min(self.calls, len(self.scripted_ids) - 1)]
        logits[0, -1, token_id] = 100.0
        self.calls += 1
        return logits


class GenerationStopTests(unittest.TestCase):
    def test_generation_stops_before_next_user_turn_marker(self):
        tokenizer = ByteBPETokenizer()
        prompt = "Jon2:"
        answer = "مرحبا"
        stop_marker = "المستخدم:"
        scripted = tokenizer.encode(answer + stop_marker)
        model = ScriptedModel(scripted)

        result = generate(
            model,
            tokenizer,
            prompt,
            "cpu",
            max_new_chars=100,
            temperature=0.8,
            stop_sequences=[stop_marker],
        )

        self.assertEqual(result, prompt + answer)
        self.assertEqual(model.calls, len(scripted))

    def test_generation_without_stop_marker_uses_token_limit(self):
        tokenizer = ByteBPETokenizer()
        model = ScriptedModel(tokenizer.encode("abc"))
        result = generate(
            model, tokenizer, "Q:", "cpu",
            max_new_chars=2, temperature=0.8,
        )
        self.assertEqual(result, "Q:ab")
        self.assertEqual(model.calls, 2)


if __name__ == "__main__":
    unittest.main()
