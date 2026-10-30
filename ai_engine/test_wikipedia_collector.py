import unittest

from collect_wikipedia_ar import clean_article_text, normalize_for_dedup


class WikipediaCorpusCollectorTests(unittest.TestCase):
    def test_cleaner_normalizes_whitespace_and_drops_noise(self):
        result = clean_article_text("  عنوان   هنا  \n\n١٢٣\nهذا نص مفيد   جدًا ")
        self.assertEqual(result, "عنوان هنا\nهذا نص مفيد جدًا")

    def test_dedup_normalization_ignores_case_and_spacing(self):
        self.assertEqual(
            normalize_for_dedup("Jon2   AI"),
            normalize_for_dedup("jon2\nAI"),
        )


if __name__ == "__main__":
    unittest.main()
