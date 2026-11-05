"""Regression tests for the Jon2 generated-answer quality guard."""
import unittest

from answer_quality import diagnose_answer, validate_generated_answer


class GeneratedAnswerQualityTests(unittest.TestCase):
    def test_accepts_plain_arabic(self):
        self.assertTrue(validate_generated_answer(
            "مرحباً! أنا مساعد تجريبي من مشروع جون2، كيف يمكنني مساعدتك؟"
        ))

    def test_rejects_latin_and_symbol_corruption(self):
        self.assertFalse(validate_generated_answer(
            "مرحبا zzz 333 ~~~ المستخدم"
        ))

    def test_rejects_repeated_subword_loop(self):
        self.assertFalse(validate_generated_answer(
            "كيفكيفكيف كيفكيفكيف هذه إجابة تجريبية"
        ))

    def test_rejects_repeated_character_loop(self):
        self.assertFalse(validate_generated_answer(
            "مرحبــــــا هذا اختبار"
        ))

    def test_rejects_empty_and_non_string(self):
        self.assertFalse(validate_generated_answer(""))
        self.assertFalse(validate_generated_answer(None))

    def test_rejects_non_arabic_answer(self):
        self.assertFalse(validate_generated_answer(
            "This is an English answer."
        ))



class EvaluationDiagnosticsTests(unittest.TestCase):
    def test_flags_empty_answer(self):
        result = diagnose_answer("")
        self.assertIn("empty_answer", result["surface_warnings"])
        self.assertTrue(result["human_semantic_review_required"])

    def test_plain_arabic_has_no_low_arabic_warning(self):
        result = diagnose_answer(
            "هذه إجابة عربية واضحة تحتوي على كلمات متنوعة ومفهومة للاختبار."
        )
        self.assertNotIn("low_arabic_character_ratio", result["surface_warnings"])

    def test_flags_repeated_word_sequence(self):
        result = diagnose_answer(
            "هذه إجابة هذه إجابة هذه إجابة هذه إجابة هذه إجابة"
        )
        self.assertIn("low_unique_word_ratio", result["surface_warnings"])

    def test_diagnostics_never_issue_quality_verdict(self):
        result = diagnose_answer("هذه إجابة عربية للاختبار فقط.")
        self.assertNotIn("quality_verdict", result)
        self.assertTrue(result["human_semantic_review_required"])


if __name__ == "__main__":
    unittest.main()
