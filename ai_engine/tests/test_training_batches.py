"""Tests for vectorized next-token mini-batch sampling."""
import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jon2_core import _batch


class TrainingBatchTests(unittest.TestCase):
    def test_batch_shapes_and_next_token_alignment(self):
        data = torch.arange(100, dtype=torch.long)
        x, y = _batch(data, context=12, batch_size=7, device="cpu")
        self.assertEqual(tuple(x.shape), (7, 12))
        self.assertEqual(tuple(y.shape), (7, 12))
        self.assertTrue(torch.equal(y, x + 1))

    def test_batch_rejects_too_short_corpus(self):
        with self.assertRaisesRegex(ValueError, "longer than context"):
            _batch(torch.arange(8), context=7, batch_size=2, device="cpu")

    def test_batch_rejects_non_positive_dimensions(self):
        data = torch.arange(32)
        with self.assertRaisesRegex(ValueError, "must be positive"):
            _batch(data, context=0, batch_size=2, device="cpu")
        with self.assertRaisesRegex(ValueError, "must be positive"):
            _batch(data, context=4, batch_size=0, device="cpu")


if __name__ == "__main__":
    unittest.main()
