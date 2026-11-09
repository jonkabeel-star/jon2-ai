import unittest

from chat_engine import build_conversation_prompt


class FakeTokenizer:
    def encode(self, text):
        # Deterministic stand-in: one token per character for budget tests.
        return list(text)


class ChatPromptTests(unittest.TestCase):
    def test_overlong_question_is_rejected_without_silent_truncation(self):
        tokenizer = FakeTokenizer()
        question = "اشرح لي الذكاء الاصطناعي " * 20
        with self.assertRaisesRegex(ValueError, "اختصر السؤال"):
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
            context=256,
        )
        self.assertIn("Jon2", prompt)
        self.assertIn("ذاكرة سابقة", prompt)
        self.assertIn("أجب بالعربية الواضحة", prompt)

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            build_conversation_prompt("   ", tokenizer=FakeTokenizer(), context=128)


if __name__ == "__main__":
    unittest.main()
