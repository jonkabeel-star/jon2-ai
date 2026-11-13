import unittest

from chat_engine import build_conversation_prompt


class FakeTokenizer:
    def encode(self, text):
        # Deterministic stand-in: one token per character for budget tests.
        return list(text)


class ChatPromptTests(unittest.TestCase):
    def test_overlong_current_question_is_rejected_without_truncation(self):
        tokenizer = FakeTokenizer()
        question = "اشرح لي الذكاء الاصطناعي " * 20
        with self.assertRaisesRegex(ValueError, "لن يتم اختصاره"):
            build_conversation_prompt(
                question,
                history=[
                    {"role": "user", "content": "سؤال قديم " * 20},
                    {"role": "assistant", "content": "إجابة قديمة " * 20},
                ],
                memories=[
                    {"role": "user", "content": "ذكرى قديمة " * 20},
                ],
                tokenizer=tokenizer,
                context=128,
            )

    def test_short_prompt_keeps_recent_context_and_memory(self):
        tokenizer = FakeTokenizer()
        prompt = build_conversation_prompt(
            "ما اسم مشروعي؟",
            history=[{"role": "assistant", "content": "أنت تطور مشروعًا اسمه Jon2."}],
            memories=[{"role": "user", "content": "اسم مشروعي Jon2."}],
            tokenizer=tokenizer,
            context=128,
        )
        self.assertIn("Jon2", prompt)
        self.assertIn("ذاكرة سابقة", prompt)


    def test_long_retrieved_context_is_reduced_before_current_question(self):
        tokenizer = FakeTokenizer()
        question = "اشرح معنى التعلم الآلي في جملة واضحة"
        reference = "مرجع: " + ("معلومة طويلة ومهمة " * 20)
        prompt = build_conversation_prompt(
            question,
            tokenizer=tokenizer,
            context=180,
            knowledge_context=reference,
        )
        self.assertIn(question, prompt)
        self.assertIn("مرجع:", prompt)
        self.assertLess(len(tokenizer.encode(prompt)), 180)
        self.assertNotIn(reference, prompt)

    def test_question_still_rejected_when_it_alone_exceeds_context(self):
        tokenizer = FakeTokenizer()
        question = "اشرح لي الذكاء الاصطناعي " * 20
        with self.assertRaisesRegex(ValueError, "لن يتم اختصاره"):
            build_conversation_prompt(
                question,
                tokenizer=tokenizer,
                context=128,
                knowledge_context="مرجع: معلومة مختصرة",
            )

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            build_conversation_prompt("   ", tokenizer=FakeTokenizer(), context=128)


if __name__ == "__main__":
    unittest.main()
