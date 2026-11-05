"""Regression tests for UTF-8-safe top-k sampling in the original Jon2 generator."""
import unittest

import torch

from tokenizer import ByteBPETokenizer
from jon2_core import generate


class InvalidTopKModel:
    context = 16

    def __call__(self, token_ids):
        batch, length = token_ids.shape
        logits = torch.zeros((batch, length, 256), device=token_ids.device)
        # The highest-scoring byte is a UTF-8 continuation byte. It is invalid
        # immediately after the complete Arabic prompt, so top-k must be
        # calculated only after invalid UTF-8 candidates have been removed.
        logits[:, :, 128] = 100.0
        return logits


class GenerationSamplingTests(unittest.TestCase):
    def test_top_k_ignores_invalid_utf8_candidates(self):
        tokenizer = ByteBPETokenizer()
        answer = generate(
            InvalidTopKModel(),
            tokenizer,
            "سؤال",
            torch.device("cpu"),
            max_new_chars=1,
            temperature=0.8,
            do_sample=True,
            top_k=1,
            no_repeat_ngram_size=0,
            repetition_penalty=1.0,
        )
        self.assertIsInstance(answer, str)
        answer.encode("utf-8", errors="strict")


if __name__ == "__main__":
    unittest.main()
