"""Offline tests for the multi-source Jon2 search engine."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import knowledge_search as search

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"JON2_KNOWLEDGE_DB_PATH":str(Path(self.temp.name)/"cache.sqlite3")})
        self.env.start(); self.addCleanup(self.env.stop); self.addCleanup(self.temp.cleanup)

    def test_ranking_prefers_title_overlap_and_deduplicates(self):
        rows=[{"title":"مصر","extract":"القاهرة عاصمة مصر","source_url":"https://a.test/x","source":"A"},{"title":"موضوع عام","extract":"معلومات مختلفة","source_url":"https://b.test/y","source":"B"},{"title":"نسخة","extract":"نص","source_url":"https://a.test/x#part","source":"C"}]
        result=search._rank("مصر القاهرة",rows)
        self.assertEqual(result[0]["source_url"],"https://a.test/x"); self.assertEqual(len(result),2)

    def test_general_search_uses_searxng_and_wikipedia_fallback(self):
        with patch.object(search,"_searxng",return_value=[]), patch.object(search,"_wikipedia",return_value=[{"title":"Cairo","extract":"Capital of Egypt","source_url":"https://en.wikipedia.org/wiki/Cairo","source":"Wikipedia","category":"web","published":None,"result_type":"article"}]), patch.dict(os.environ,{"JON2_SEARXNG_URL":"https://search.example"}):
            result=search.search_knowledge("Cairo Egypt",category="web")
        self.assertEqual(result["status"],"ok"); self.assertIn("Wikipedia",result["sources_used"])

    def test_science_search_aggregates_multiple_open_sources(self):
        a={"title":"Paper A","extract":"Abstract","source_url":"https://doi.org/a","source":"Crossref","category":"science"}
        b={"title":"Paper B","extract":"Research","source_url":"https://openalex.org/b","source":"OpenAlex","category":"science"}
        with patch.object(search,"_crossref",return_value=[a]), patch.object(search,"_openalex",return_value=[b]), patch.object(search,"_europe_pmc",return_value=[]):
            result=search.search_knowledge("arabic language model",category="science")
        self.assertEqual(len(result["results"]),2); self.assertEqual(set(result["sources_used"]),{"Crossref","OpenAlex"})

    def test_news_search_uses_selected_time_range(self):
        with patch.object(search,"_gdelt_news",return_value=[]) as news:
            search.search_knowledge("Egypt",category="news",time_range="week")
        news.assert_called_once_with("Egypt","week")

    def test_cache_is_scoped_by_category_and_time(self):
        with patch.object(search,"_wikipedia",return_value=[]), patch.object(search,"_gdelt_news",return_value=[]):
            first=search.search_knowledge("test query",category="web"); second=search.search_knowledge("test query",category="web"); third=search.search_knowledge("test query",category="news")
        self.assertFalse(first["cached"]); self.assertTrue(second["cached"]); self.assertFalse(third["cached"])

    def test_input_validation(self):
        with self.assertRaises(ValueError): search.search_knowledge("x"*501)
        with self.assertRaises(ValueError): search.search_knowledge("valid query",category="unknown")
        with self.assertRaises(ValueError): search.search_knowledge("valid query",time_range="forever")

    def test_no_results_never_claim_an_answer(self):
        result=search.answer_from_sources({"results":[]})
        self.assertIsNone(result["answer"]); self.assertEqual(result["answer_type"],"no_verified_retrieval")

    def test_retrieved_answer_keeps_source_attribution(self):
        result=search.answer_from_sources({"results":[{"title":"Title","extract":"Evidence","source_url":"https://example.org","source":"OpenAlex","relevance":0.9}]})
        self.assertEqual(result["answer"],"Evidence"); self.assertEqual(result["sources"][0]["source"],"OpenAlex")

if __name__=="__main__": unittest.main()
