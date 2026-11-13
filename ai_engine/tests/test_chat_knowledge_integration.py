"""Offline integration tests for source-backed knowledge in the public chat route.

These tests mock all network and model calls. They verify the API wiring, not
Wikipedia availability or factual correctness.
"""
import unittest
from unittest.mock import patch

import main


class ChatKnowledgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.release = patch.object(main, "_chat_release_approved", return_value=True)
        self.release.start()
        self.addCleanup(self.release.stop)

    def test_retrieved_fact_is_returned_with_source_without_loading_model(self):
        item = {
            "title": "قناة السويس",
            "extract": "ممر مائي صناعي في مصر يربط البحر المتوسط بالبحر الأحمر.",
            "source_url": "https://ar.wikipedia.org/wiki/قناة_السويس",
            "cached": False,
        }
        with (
            patch.object(main, "local_greeting", return_value=None),
            patch.object(main, "looks_like_fact_question", return_value=True),
            patch.object(main, "retrieve_knowledge", return_value=item) as retrieve,
            patch.object(main, "format_knowledge_answer", return_value="قناة السويس: شرح\nالمصدر: https://ar.wikipedia.org/wiki/قناة_السويس"),
            patch.object(main, "generate_reply") as generate,
            patch.object(main.chat_memory, "add_exchange") as save,
        ):
            response = main.chat(main.ChatRequest(message="ما هي قناة السويس؟", session_id=None))

        self.assertTrue(response["knowledge_used"])
        self.assertEqual(response["response_mode"], "source_retrieval")
        self.assertEqual(response["knowledge_source"], item["source_url"])
        self.assertIn("المصدر:", response["reply"])
        retrieve.assert_called_once_with("ما هي قناة السويس؟")
        generate.assert_not_called()
        save.assert_not_called()

    def test_retrieval_failure_falls_back_to_original_model_path(self):
        with (
            patch.object(main, "local_greeting", return_value=None),
            patch.object(main, "looks_like_fact_question", return_value=True),
            patch.object(main, "retrieve_knowledge", return_value=None),
            patch.object(main, "generate_reply", return_value="إجابة تجريبية"),
        ):
            response = main.chat(main.ChatRequest(message="ما عاصمة مصر؟"))

        self.assertEqual(response["reply"], "إجابة تجريبية")
        self.assertNotIn("knowledge_used", response)

    def test_greeting_short_circuits_retrieval_and_model(self):
        with (
            patch.object(main, "local_greeting", return_value="أهلًا وسهلًا!") as greeting,
            patch.object(main, "retrieve_knowledge") as retrieve,
            patch.object(main, "generate_reply") as generate,
        ):
            response = main.chat(main.ChatRequest(message="مرحبا"))

        self.assertEqual(response["response_mode"], "local_greeting")
        self.assertFalse(response["knowledge_used"])
        greeting.assert_called_once_with("مرحبا")
        retrieve.assert_not_called()
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
