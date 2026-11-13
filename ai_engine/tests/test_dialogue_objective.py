"""Tests for assistant-only supervised training of the original Jon2 model."""
import sys
import tempfile
import unittest
from pathlib import Path

import torch

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from dialogue_objective import (
    assistant_only_batch,
    encode_assistant_only,
    load_dialogue_records,
    masked_language_model_loss,
    split_dialogues,
)
from tokenizer import ByteBPETokenizer


class DialogueObjectiveTests(unittest.TestCase):
    def setUp(self):
        self.conversations = [
            [
                {"role": "user", "content": "ما عاصمة مصر؟"},
                {"role": "assistant", "content": "عاصمة مصر هي القاهرة."},
            ],
            [
                {"role": "user", "content": "كم يساوي اثنان زائد ثلاثة؟"},
                {"role": "assistant", "content": "الناتج خمسة."},
            ],
            [
                {"role": "user", "content": "ما لون السماء نهارًا؟"},
                {"role": "assistant", "content": "تبدو السماء زرقاء غالبًا."},
            ],
        ]
        text = " ".join(
            message["content"]
            for conversation in self.conversations
            for message in conversation
        )
        self.tokenizer = ByteBPETokenizer.train(text, vocab_size=300)

    def test_loss_mask_contains_only_assistant_content(self):
        tokens, mask = encode_assistant_only(self.conversations[:1], self.tokenizer)
        selected = self.tokenizer.decode(tokens[mask].tolist())
        self.assertIn("عاصمة مصر هي القاهرة.", selected)
        self.assertNotIn("ما عاصمة مصر؟", selected)

    def test_split_keeps_whole_conversations_and_is_repeatable(self):
        train_a, val_a = split_dialogues(self.conversations, 0.34, 42)
        train_b, val_b = split_dialogues(self.conversations, 0.34, 42)
        self.assertEqual(train_a, train_b)
        self.assertEqual(val_a, val_b)
        self.assertEqual(len(train_a) + len(val_a), len(self.conversations))
        self.assertFalse(set(map(id, train_a)) & set(map(id, val_a)))

    def test_batch_always_has_assistant_targets(self):
        tokens, mask = encode_assistant_only(self.conversations, self.tokenizer)
        x, y, target_mask = assistant_only_batch(
            tokens, mask, context=16, batch_size=4, device="cpu"
        )
        self.assertEqual(tuple(x.shape), (4, 16))
        self.assertEqual(tuple(y.shape), (4, 16))
        self.assertEqual(tuple(target_mask.shape), (4, 16))
        self.assertTrue(target_mask.any(dim=1).all())

    def test_masked_loss_is_finite_and_rejects_empty_mask(self):
        targets = torch.tensor([[1, 2, 3]])
        logits = torch.randn(1, 3, 8, requires_grad=True)
        mask = torch.tensor([[False, True, False]])
        loss = masked_language_model_loss(logits, targets, mask)
        self.assertTrue(torch.isfinite(loss))
        with self.assertRaisesRegex(ValueError, "empty target mask"):
            masked_language_model_loss(logits, targets, torch.zeros_like(mask))

    def test_jsonl_loader_rejects_non_alternating_turns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.jsonl"
            path.write_text(
                '{"messages":[{"role":"user","content":"سؤال"},{"role":"user","content":"سؤال آخر"},{"role":"assistant","content":"إجابة"}]}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "alternate"):
                load_dialogue_records(directory)


if __name__ == "__main__":
    unittest.main()
