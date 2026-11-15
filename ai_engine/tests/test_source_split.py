"""Tests for source-isolated corpus splitting and leakage detection."""
import unittest

from source_split import split_corpus_sources


class SourceSplitTests(unittest.TestCase):
    def test_keeps_each_source_wholly_in_one_partition(self):
        sources = [
            ("owner_a.txt", "A1\n\nA2"),
            ("owner_b.txt", "B1\n\nB2"),
            ("owner_c.txt", "C1\n\nC2"),
            ("owner_d.txt", "D1\n\nD2"),
        ]
        train, validation = split_corpus_sources(sources, 0.25, 42)
        for prefix in "ABCD":
            in_train = prefix in train
            in_validation = prefix in validation
            self.assertNotEqual(in_train, in_validation)

    def test_blocks_normalized_duplicate_paragraphs_across_splits(self):
        sources = [
            ("a.txt", "مرحبا يا صديقي"),
            ("b.txt", "مَرْحَبًا   يا صديقي"),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate content crosses"):
            split_corpus_sources(sources, 0.25, 1)

    def test_requires_two_independent_sources(self):
        with self.assertRaisesRegex(ValueError, "At least two"):
            split_corpus_sources([("only.txt", "نص واحد")], 0.1, 42)

    def test_rejects_duplicate_source_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate corpus source ID"):
            split_corpus_sources([("same.txt", "A"), ("same.txt", "B")], 0.25, 42)

    def test_is_deterministic(self):
        sources = [(f"{i}.txt", f"unique text {i}") for i in range(10)]
        self.assertEqual(
            split_corpus_sources(sources, 0.2, 7),
            split_corpus_sources(sources, 0.2, 7),
        )


if __name__ == "__main__":
    unittest.main()
