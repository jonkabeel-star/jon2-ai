"""Regression tests for Jon2's Arabic output guardrails.

Run from the repository root:
    python -m unittest discover -s ai_engine/tests -v
"""
import sys
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from answer_quality import diagnose_answer, validate_generated_answer


class ArabicAnswerQualityTests(unittest.TestCase):
    def test_accepts_clear_arabic_answer(self):
        answer = "الذكاء الاصطناعي هو مجال يطوّر أنظمة تنفّذ مهام تحتاج عادةً إلى قدرات بشرية."
        self.assertTrue(validate_generated_answer(answer))

    def test_rejects_empty_and_too_short_answers(self):
        self.assertFalse(validate_generated_answer(""))
        self.assertFalse(validate_generated_answer("نعم"))

    def test_rejects_unexpected_latin_script(self):
        self.assertFalse(validate_generated_answer("هذه إجابة عربية mixed with English words"))

    def test_rejects_obvious_character_loop(self):
        self.assertFalse(validate_generated_answer("هذااااا نص عربي غير سليم"))

    def test_rejects_repeated_phrase_loop(self):
        self.assertFalse(
            validate_generated_answer("كلام واضح كلام واضح كلام واضح كلام واضح")
        )

    def test_accepts_normal_arabic_punctuation_and_digits(self):
        self.assertTrue(validate_generated_answer("الناتج هو ٥٤، لأن ٦ × ٩ = ٥٤."))

    def test_diagnostics_flag_empty_answer(self):
        result = diagnose_answer("")
        self.assertIn("empty_answer", result["surface_warnings"])
        self.assertTrue(result["human_semantic_review_required"])

    def test_diagnostics_flag_low_arabic_ratio(self):
        result = diagnose_answer("This is mostly English text")
        self.assertIn("low_arabic_character_ratio", result["surface_warnings"])

    def test_diagnostics_flag_repeated_three_word_sequence(self):
        result = diagnose_answer("هذا نص عربي هذا نص عربي")
        self.assertIn("repeated_three_word_sequence", result["surface_warnings"])

    def test_diagnostics_do_not_claim_semantic_approval(self):
        result = diagnose_answer("إجابة عربية واضحة ومترابطة للاختبار.")
        self.assertIsNone(result.get("quality_score"))
        self.assertTrue(result["human_semantic_review_required"])


if __name__ == "__main__":
    unittest.main()
