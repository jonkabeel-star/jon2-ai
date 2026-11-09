import unittest

from arabic_response import (
    clean_generated_answer,
    diagnose_arabic_answer,
    validate_arabic_answer,
)
from chat_engine import build_conversation_prompt


class ArabicResponseTests(unittest.TestCase):
    def test_cleanup_removes_role_prefix_and_formatting_noise(self):
        raw = "Jon2:  الطاقة الشمسية  ،\n\n\nتحول ضوء الشمس إلى كهرباء."
        self.assertEqual(
            clean_generated_answer(raw),
            "الطاقة الشمسية،\n\nتحول ضوء الشمس إلى كهرباء.",
        )

    def test_clear_arabic_answer_passes_surface_checks(self):
        answer = "الطاقة الشمسية تحول ضوء الشمس إلى كهرباء باستخدام الألواح."
        self.assertTrue(validate_arabic_answer(answer))
        report = diagnose_arabic_answer(
            answer, question="كيف تنتج الألواح الشمسية الكهرباء؟"
        )
        self.assertGreaterEqual(report["arabic_character_ratio"], 0.70)
        self.assertFalse(report["semantic_correctness_verified"])
        self.assertTrue(report["human_semantic_review_required"])

    def test_repeated_sentence_is_rejected(self):
        sentence = "الماء ضروري لحياة الإنسان."
        self.assertFalse(validate_arabic_answer(sentence + " " + sentence))

    def test_latin_or_corrupted_output_is_rejected(self):
        self.assertFalse(validate_arabic_answer("Hello world this is a response"))
        self.assertFalse(validate_arabic_answer("هذه إجابة تالفة � ولا تصلح للعرض"))

    def test_repeated_word_loop_is_rejected(self):
        self.assertFalse(
            validate_arabic_answer(
                "هذا جواب هذا جواب هذا جواب هذا جواب هذا جواب"
            )
        )

    def test_question_overlap_is_diagnostic_not_a_false_rejection(self):
        answer = "تشرق الشمس من جهة الشرق وتغرب من جهة الغرب."
        report = diagnose_arabic_answer(answer, question="ما لون حقيبة المدرسة؟")
        self.assertIn("low_lexical_overlap_review", report["warnings"])
        self.assertTrue(validate_arabic_answer(answer, question="ما لون حقيبة المدرسة؟"))


class PromptSafetyTests(unittest.TestCase):
    class CharacterCountingTokenizer:
        def encode(self, text):
            return list(text)

    def test_prompt_includes_short_arabic_instruction(self):
        prompt = build_conversation_prompt(
            "اشرح الطاقة الشمسية",
            tokenizer=self.CharacterCountingTokenizer(),
            context=256,
        )
        self.assertIn("أجب بالعربية الواضحة", prompt)
        self.assertIn("اشرح الطاقة الشمسية", prompt)

    def test_long_question_is_rejected_instead_of_silently_truncated(self):
        question = "اشرح بالتفصيل " + ("الطاقة الشمسية " * 20)
        with self.assertRaisesRegex(ValueError, "اختصر السؤال"):
            build_conversation_prompt(
                question,
                tokenizer=self.CharacterCountingTokenizer(),
                context=64,
            )


if __name__ == "__main__":
    unittest.main()
