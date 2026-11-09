import unittest
from pathlib import Path

from evaluate_model import load_prompts


class EgyptianArabicEvaluationSetTests(unittest.TestCase):
    def test_egyptian_prompts_are_valid_and_held_out(self):
        path = Path(__file__).resolve().parent / "evaluation" / "prompts_egyptian_ar.jsonl"
        prompts = load_prompts(path)
        self.assertEqual(len(prompts), 20)
        self.assertEqual(len({item["id"] for item in prompts}), 20)
        combined = " ".join(item["prompt"] for item in prompts)
        self.assertIn("مش فاهم", combined)
        self.assertIn("مش هروح", combined)
        self.assertIn("لو مش عارف", combined)


if __name__ == "__main__":
    unittest.main()
