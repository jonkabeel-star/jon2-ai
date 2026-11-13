"""Tests that retrieved source text is supplied as context, not returned as an answer."""

import unittest

import chat_engine


class WhitespaceTokenizer:
    def encode(self, text):
        return text.split()


class KnowledgePromptContextTests(unittest.TestCase):
    def test_retrieved_facts_are_context_for_model_synthesis(self):
        question = "ما عاصمة مصر؟"
        source_context = "القاهرة: القاهرة هي عاصمة جمهورية مصر العربية."
        prompt = chat_engine.build_conversation_prompt(
            question,
            tokenizer=WhitespaceTokenizer(),
            context=128,
            knowledge_context=source_context,
        )

        self.assertIn("معلومات مرجعية مسترجعة", prompt)
        self.assertIn("أجب بصياغتك أنت", prompt)
        self.assertIn(source_context, prompt)
        self.assertIn(question, prompt)
        self.assertTrue(prompt.endswith("Jon2:"))

    def test_oversized_reference_context_fails_without_truncating_question(self):
        question = "ما عاصمة مصر؟"
        with self.assertRaisesRegex(ValueError, "لن يتم حذف السؤال أو اختصاره"):
            chat_engine.build_conversation_prompt(
                question,
                tokenizer=WhitespaceTokenizer(),
                context=8,
                knowledge_context="معلومة مرجعية طويلة " * 30,
            )


if __name__ == "__main__":
    unittest.main()
