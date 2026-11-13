"""Regression tests for lossless conversation-context construction."""

import unittest

import chat_engine


class WhitespaceTokenizer:
    def encode(self, text):
        return text.split()


class ConversationContextTests(unittest.TestCase):
    def test_drops_old_history_before_preserving_the_complete_current_question(self):
        question = "اشرح لي الفرق بين التعلم العميق والتعلم الآلي"
        prompt = chat_engine.build_conversation_prompt(
            question,
            history=[
                {"role": "user", "content": "رسالة قديمة طويلة لا نحتاجها في هذا الاختبار"},
                {"role": "assistant", "content": "رد قديم طويل لا نحتاجه في هذا الاختبار"},
            ],
            tokenizer=WhitespaceTokenizer(),
            context=15,
        )

        self.assertIn(question, prompt)
        self.assertNotIn("رسالة قديمة", prompt)
        self.assertTrue(prompt.endswith("Jon2:"))

    def test_rejects_question_that_cannot_fit_without_truncating_it(self):
        question = "اشرح بالتفصيل كيف تؤثر الذاكرة والسياق على فهم السؤال العربي"
        with self.assertRaisesRegex(ValueError, "لن يتم اختصاره"):
            chat_engine.build_conversation_prompt(
                question,
                tokenizer=WhitespaceTokenizer(),
                context=8,
            )


if __name__ == "__main__":
    unittest.main()
