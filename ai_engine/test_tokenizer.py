"""Unit tests for Jon2's byte-level BPE tokenizer."""
import tempfile
import unittest
from pathlib import Path

from tokenizer import ByteBPETokenizer


class ByteBPETokenizerTests(unittest.TestCase):
    def test_round_trip_arabic_english_emoji_and_punctuation(self):
        training_text = "مرحبًا بك في Jon2 AI! مرحبًا بك في Jon2 AI! 🚀"
        tokenizer = ByteBPETokenizer.train(training_text, vocab_size=320)
        sample = "مرحبًا! Jon2 — اختبار عربي 😊"
        self.assertEqual(tokenizer.decode(tokenizer.encode(sample)), sample)

    def test_unseen_characters_use_byte_fallback(self):
        tokenizer = ByteBPETokenizer.train("نص عربي متكرر " * 10, vocab_size=300)
        sample = "漢字 🧪"
        self.assertEqual(tokenizer.decode(tokenizer.encode(sample)), sample)

    def test_training_is_deterministic(self):
        text = "السلام عليكم. السلام عليكم. أهلاً بك."
        first = ByteBPETokenizer.train(text, vocab_size=300).to_dict()
        second = ByteBPETokenizer.train(text, vocab_size=300).to_dict()
        self.assertEqual(first, second)

    def test_save_and_load_preserve_encoding(self):
        text = "Jon2 يتعلم العربية خطوة بخطوة. " * 8
        tokenizer = ByteBPETokenizer.train(text, vocab_size=320)
        sample = "تجربة جديدة للمنصة."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokenizer.json"
            tokenizer.save(path)
            restored = ByteBPETokenizer.load(path)
        self.assertEqual(restored.encode(sample), tokenizer.encode(sample))
        self.assertEqual(restored.decode(restored.encode(sample)), sample)

    def test_rejects_invalid_merge_table(self):
        with self.assertRaises(ValueError):
            ByteBPETokenizer.from_dict({
                "format": "jon2-byte-bpe-v1",
                "base_vocab_size": 256,
                "merges": [[256, 1]],
            })


if __name__ == "__main__":
    unittest.main()
