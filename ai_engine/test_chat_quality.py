"""Regression tests for the Jon2 generated-answer quality guard."""
import unittest

from chat_engine import validate_generated_answer


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


if __name__ == "__main__":
    unittest.main()
