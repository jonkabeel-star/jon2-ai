"""Offline tests for the source-attributed knowledge search engine."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge_search as search


class KnowledgeSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "JON2_KNOWLEDGE_DB_PATH": str(Path(self.temp.name) / "knowledge.sqlite3")
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)

    def test_rank_prefers_title_match(self):
        ranked = search._rank("ما عاصمة مصر", [
            {"title": "الجغرافيا", "extract": "تتضمن معلومات عن القاهرة ومصر"},
            {"title": "مصر", "extract": "القاهرة هي عاصمة مصر"},
        ])
        self.assertEqual(ranked[0]["title"], "مصر")
        self.assertGreaterEqual(ranked[0]["relevance"], ranked[1]["relevance"])

    def test_search_returns_multiple_attributed_results(self):
        pages = [("القاهرة", ""), ("مصر", "")]
        summaries = [
            {"title": title, "extract": f"معلومات عن {title}", "source_url": f"https://ar.wikipedia.org/wiki/{title}", "language": "ar"}
            for title, _ in pages
        ]
        with patch.object(search, "_candidate_pages", return_value=pages), \
             patch.object(search, "_summary", side_effect=summaries):
            result = search.search_knowledge("ما عاصمة مصر؟", limit=2)
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(all(item["source_url"].startswith("https://") for item in result["results"]))
        self.assertEqual(result["source_policy"], "retrieval_only_not_training")

    def test_search_cache_prevents_second_fetch(self):
        page = [("القاهرة", "")]
        summary = {"title": "القاهرة", "extract": "عاصمة مصر", "source_url": "https://ar.wikipedia.org/wiki/Cairo", "language": "ar"}
        with patch.object(search, "_candidate_pages", return_value=page) as fetch, \
             patch.object(search, "_summary", return_value=summary):
            first = search.search_knowledge("القاهرة عاصمة مصر")
            second = search.search_knowledge("القاهرة عاصمة مصر")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        fetch.assert_called_once()

    def test_query_length_is_bounded(self):
        with self.assertRaises(ValueError):
            search.search_knowledge("س" * 501)

    def test_empty_results_do_not_claim_answer(self):
        result = search.answer_from_sources({"results": []})
        self.assertIsNone(result["answer"])
        self.assertEqual(result["answer_type"], "no_verified_retrieval")

    def test_answer_is_explicitly_labeled_as_retrieval(self):
        result = search.answer_from_sources({"results": [{
            "title": "عنوان", "extract": "معلومة موثقة", "source_url": "https://ar.wikipedia.org/wiki/Test", "relevance": 0.8
        }]})
        self.assertEqual(result["answer"], "معلومة موثقة")
        self.assertEqual(result["answer_type"], "retrieved_source_extract")
        self.assertIn("ليس إجابة مولّدة", result["notice"])

    def test_weak_match_is_not_presented_as_answer(self):
        result = search.answer_from_sources({"results": [{
            "title": "عنوان", "extract": "نص", "source_url": "https://ar.wikipedia.org/wiki/Test", "relevance": 0.01
        }]})
        self.assertIsNone(result["answer"])
        self.assertEqual(result["answer_type"], "weak_match")


if __name__ == "__main__":
    unittest.main()
