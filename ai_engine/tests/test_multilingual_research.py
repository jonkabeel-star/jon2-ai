"""Offline regression tests for multilingual source-backed research routing."""
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import knowledge_engine as knowledge


class MultilingualResearchTests(unittest.TestCase):
    def test_detects_supported_writing_systems(self):
        cases = {
            "ما عاصمة مصر؟": "ar",
            "東京の歴史": "ja",
            "北京在哪里": "zh",
            "서울의 역사": "ko",
            "Москва": "ru",
            "भारत की राजधानी": "hi",
            "ประเทศไทย": "th",
            "Ελλάδα": "el",
            "שלום עולם": "he",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(knowledge.detect_query_language(text), expected)

    def test_detects_common_latin_languages(self):
        cases = {
            "What is artificial intelligence?": "en",
            "Qu'est-ce que la photosynthèse": "fr",
            "¿Qué es la inteligencia artificial?": "es",
            "Was ist künstliche Intelligenz": "de",
            "Che cos'è la fotosintesi": "it",
            "O que é inteligência artificial": "pt",
            "Wat is kunstmatige intelligentie": "nl",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(knowledge.detect_query_language(text), expected)

    def test_english_question_is_routed_to_english_wikipedia(self):
        with patch.object(knowledge, "_fetch_json", side_effect=[
            {"query": {"search": [{"title": "Artificial intelligence"}]}},
            {"extract": "Artificial intelligence is a field.", "content_urls": {
                "desktop": {"page": "https://en.wikipedia.org/wiki/Artificial_intelligence"}
            }},
        ]) as fetch:
            item = knowledge._search_wikipedia("What is artificial intelligence?")
        self.assertEqual(item["language"], "en")
        self.assertIn("en.wikipedia.org/w/api.php", fetch.call_args_list[0].args[0])

    def test_spanish_question_is_routed_to_spanish_wikipedia(self):
        with patch.object(knowledge, "_fetch_json", side_effect=[
            {"query": {"search": [{"title": "Inteligencia artificial"}]}},
            {"extract": "La inteligencia artificial es un campo.", "content_urls": {
                "desktop": {"page": "https://es.wikipedia.org/wiki/Inteligencia_artificial"}
            }},
        ]) as fetch:
            item = knowledge._search_wikipedia("¿Qué es la inteligencia artificial?")
        self.assertEqual(item["language"], "es")
        query = parse_qs(urlparse(fetch.call_args_list[0].args[0]).query)
        self.assertEqual(query["srsearch"], ["¿Qué es la inteligencia artificial?"])

    def test_question_detection_in_multiple_languages(self):
        self.assertTrue(knowledge.looks_like_fact_question("What is gravity?"))
        self.assertTrue(knowledge.looks_like_fact_question("¿Qué es la fotosíntesis?"))
        self.assertTrue(knowledge.looks_like_fact_question("Was ist Energie?"))
        self.assertTrue(knowledge.looks_like_fact_question("ما عاصمة مصر؟"))
        self.assertFalse(knowledge.looks_like_fact_question("Write a short story"))


if __name__ == "__main__":
    unittest.main()
