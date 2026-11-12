"""Regression tests for the authored, held-out Arabic evaluation set.

These tests validate benchmark structure only. They do not evaluate model quality.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_checkpoint import PROMPT_SETS


class ArabicHoldoutPromptTests(unittest.TestCase):
    def test_both_arabic_registers_have_independent_cases(self):
        self.assertEqual(set(PROMPT_SETS), {"msa", "egyptian"})
        self.assertGreaterEqual(len(PROMPT_SETS["msa"]), 10)
        self.assertGreaterEqual(len(PROMPT_SETS["egyptian"]), 10)

    def test_prompts_are_nonempty_and_unique(self):
        all_prompts = []
        for dialect, prompts in PROMPT_SETS.items():
            with self.subTest(dialect=dialect):
                self.assertTrue(all(isinstance(p, str) and p.strip() for p in prompts))
            all_prompts.extend(prompts)
        self.assertEqual(len(all_prompts), len(set(all_prompts)))

    def test_prompt_sets_are_not_accidentally_mixed(self):
        # Lightweight lexical guard: Egyptian set must contain colloquial cues;
        # MSA set must not simply duplicate the Egyptian set.
        egyptian_text = " ".join(PROMPT_SETS["egyptian"])
        self.assertTrue(any(token in egyptian_text for token in ("بص", "عايز", "إيه", "معايا")))
        self.assertFalse(set(PROMPT_SETS["msa"]) & set(PROMPT_SETS["egyptian"]))

    def test_benchmark_size_is_24_and_dialect_balanced(self):
        self.assertEqual(len(PROMPT_SETS["msa"]), 12)
        self.assertEqual(len(PROMPT_SETS["egyptian"]), 12)

    def test_evaluation_is_not_an_automatic_release_approval(self):
        source = (Path(__file__).resolve().parents[1] / "evaluate_checkpoint.py").read_text(encoding="utf-8")
        self.assertIn('"semantic_quality": "HUMAN_REVIEW_REQUIRED"', source)
        self.assertIn('"approved_for_release": False', source)
        self.assertIn('"factuality_passed": False', source)


if __name__ == "__main__":
    unittest.main()
