"""Offline tests for Jon2's local knowledge cache and greeting path."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import knowledge_engine as knowledge


class KnowledgeEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"JON2_KNOWLEDGE_DB_PATH": str(Path(self.temp.name) / "knowledge.sqlite3")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)

    def test_greeting_is_answered_without_web(self):
        self.assertIn("أهلًا", knowledge.local_greeting("مرحبا"))
        self.assertIsNone(knowledge.local_greeting("اشرح الذكاء الاصطناعي"))

    def test_identity_question_is_answered_without_model(self):
        for question in ("انت اسمك ايه", "ما اسمك؟", "اسم المساعد ايه"):
            self.assertIn("Jon2 AI", knowledge.local_identity(question))
        self.assertIsNone(knowledge.local_identity("ما اسم عاصمة مصر؟"))

    def test_cache_persists_source_and_extract(self):
        record = {"title": "الذكاء الاصطناعي", "extract": "مجال علمي.", "source_url": "https://ar.wikipedia.org/wiki/AI"}
        knowledge.store("ما هو الذكاء الاصطناعي؟", record, now=100)
        cached = knowledge.get_cached("ما هو الذكاء الاصطناعي؟", now=101)
        self.assertEqual(cached["title"], record["title"])
        self.assertEqual(cached["source_url"], record["source_url"])

    def test_expired_cache_is_not_returned(self):
        record = {"title": "عنوان", "extract": "شرح", "source_url": "https://ar.wikipedia.org/wiki/Test"}
        knowledge.store("اختبار", record, now=100)
        self.assertIsNone(knowledge.get_cached("اختبار", now=100 + knowledge.CACHE_TTL_SECONDS + 1))

    def test_retrieval_fetches_once_then_uses_cache(self):
        record = {"title": "عنوان", "extract": "شرح مختصر", "source_url": "https://ar.wikipedia.org/wiki/Test"}
        with patch.object(knowledge, "_search_wikipedia", return_value=record) as search:
            first = knowledge.retrieve_knowledge("ما هو الاختبار؟")
            second = knowledge.retrieve_knowledge("ما هو الاختبار؟")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        search.assert_called_once()

    def test_invalid_source_is_rejected(self):
        with self.assertRaises(ValueError):
            knowledge.store("اختبار", {"title": "عنوان", "extract": "شرح", "source_url": "http://invalid"})

    def test_question_search_strips_arabic_wrapper(self):
        with patch.object(knowledge, "_fetch_json", side_effect=[
            {"query": {"search": [{"title": "الذكاء الاصطناعي"}]}},
            {"extract": "مجال علمي.", "content_urls": {"desktop": {"page": "https://ar.wikipedia.org/wiki/AI"}}},
        ]) as fetch:
            result = knowledge._search_wikipedia("ما هو الذكاء الاصطناعي؟")
        self.assertEqual(result["title"], "الذكاء الاصطناعي")
        self.assertEqual(parse_qs(urlparse(fetch.call_args_list[0].args[0]).query)["srsearch"], ["الذكاء الاصطناعي"])

    def test_network_failure_is_safe(self):
        with patch.object(knowledge, "_search_wikipedia", side_effect=TimeoutError("offline")):
            self.assertIsNone(knowledge.retrieve_knowledge("ما عاصمة مصر؟"))

    def test_question_detection(self):
        self.assertTrue(knowledge.looks_like_fact_question("اشرح الذكاء الاصطناعي"))
        self.assertTrue(knowledge.looks_like_fact_question("ما عاصمة مصر؟"))
        self.assertFalse(knowledge.looks_like_fact_question("اكتب قصة قصيرة"))


if __name__ == "__main__":
    unittest.main()
