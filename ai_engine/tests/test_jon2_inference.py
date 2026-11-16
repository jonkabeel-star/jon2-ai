"""CPU-only tests for Jon2 inference, dialect, safety, and completion contracts."""
import unittest
from ai_engine.jon2_inference import (
    DEFAULT_MAX_NEW_TOKENS, JON2_SYSTEM_PROMPT, MAX_ALLOWED_NEW_TOKENS,
    classify_finish_reason, max_new_tokens_for, sanitize_safety_answer,
    with_jon2_system_prompt,
)

class Jon2InferenceTests(unittest.TestCase):
    def test_prompt_contains_egyptian_dialect_rules(self):
        self.assertIn("المصري الطبيعي", JON2_SYSTEM_PROMPT)
        self.assertIn("شنو", JON2_SYSTEM_PROMPT)
        self.assertIn("ما تناديش المستخدم باسم", JON2_SYSTEM_PROMPT)\n        self.assertIn("اكتب كلمتين فقط", JON2_SYSTEM_PROMPT)\n        self.assertIn("اكتب الرسالة الجاهزة مباشرة", JON2_SYSTEM_PROMPT)\n        self.assertIn("اسأل سؤال توضيحي واحد", JON2_SYSTEM_PROMPT)

    def test_prompt_contains_honesty_and_safety_rules(self):
        self.assertIn("ما تخترعش أرقام", JON2_SYSTEM_PROMPT)
        self.assertIn("ممنوع اختراع أو تخمين أرقام الطوارئ", JON2_SYSTEM_PROMPT)
        self.assertIn("هواء طلق", JON2_SYSTEM_PROMPT)

    def test_adds_prompt_without_mutating_history(self):
        original = [{"role": "user", "content": "إزيك؟"}]
        result = with_jon2_system_prompt(original)
        self.assertEqual(original, [{"role": "user", "content": "إزيك؟"}])
        self.assertEqual(result[0]["role"], "system")
        self.assertEqual(result[1]["content"], "إزيك؟")

    def test_existing_system_prompt_is_extended_once(self):
        messages = [{"role": "system", "content": "قواعد"}, {"role": "user", "content": "سؤال"}]
        once = with_jon2_system_prompt(messages)
        self.assertEqual(once, with_jon2_system_prompt(once))

    def test_task_budgets_are_bounded(self):
        self.assertEqual(max_new_tokens_for("eg_greeting"), 64)
        self.assertEqual(max_new_tokens_for("eg_multi_step"), 384)\n        self.assertEqual(max_new_tokens_for("reg_short_answer"), 64)\n        self.assertEqual(max_new_tokens_for("reg_friendly_apology"), 128)
        self.assertEqual(max_new_tokens_for("eg_safety"), 256)
        self.assertEqual(max_new_tokens_for("unknown"), DEFAULT_MAX_NEW_TOKENS)
        self.assertLessEqual(max_new_tokens_for("eg_multi_step"), MAX_ALLOWED_NEW_TOKENS)

    def test_rejects_invalid_budgets(self):
        for value in (0, -1, True, MAX_ALLOWED_NEW_TOKENS + 1):
            with self.assertRaises(ValueError):
                max_new_tokens_for("eg_greeting", value)

    def test_safety_phone_number_is_replaced(self):
        unsafe = "اتصل بالرقم 123 أو 155 لو تعبت."
        cleaned = sanitize_safety_answer(unsafe, "eg_safety")
        self.assertNotIn("123", cleaned)
        self.assertNotIn("155", cleaned)
        self.assertIn("خدمات الطوارئ المحلية", cleaned)\n\n    def test_sanitizer_removes_unverified_phone_digits_without_call_word(self):\n        unsafe = "رقم الطوارئ 123 أو 155."\n        cleaned = sanitize_safety_answer(unsafe, "eg_safety")\n        self.assertNotIn("123", cleaned)\n        self.assertNotIn("155", cleaned)\n        self.assertIn("رقم غير متحقق", cleaned)

    def test_sanitizer_does_not_change_non_safety_answers(self):
        answer = "اتصل بالرقم 123 لحجز موعد."
        self.assertEqual(sanitize_safety_answer(answer, "eg_writing"), answer)

    def test_eos_is_clean_stop(self):
        self.assertEqual(classify_finish_reason(10, 64, 2, [1, 2]), "stop")

    def test_budget_exhaustion_is_length(self):
        self.assertEqual(classify_finish_reason(64, 64, 9, [1, 2]), "length")

    def test_early_stop_without_eos_is_stop(self):
        self.assertEqual(classify_finish_reason(20, 64, 9, [1, 2]), "stop")

if __name__ == "__main__":
    unittest.main()
