import unittest

from ai_engine.evaluate_staged_arabic import CONVERSATIONS, SENTENCES, SINGLE_WORDS


class StagedArabicBenchmarkTests(unittest.TestCase):
    def test_single_word_cases_cover_common_intents(self):
        intents = {intent for _, intent in SINGLE_WORDS}
        self.assertTrue({"greeting", "gratitude", "why_question", "help_request", "negation", "affirmation"}.issubset(intents))
        self.assertGreaterEqual(len(SINGLE_WORDS), 10)

    def test_sentence_cases_cover_fusha_and_egyptian(self):
        dialects = {dialect for dialect, _ in SENTENCES}
        self.assertEqual(dialects, {"msa", "egyptian"})

    def test_context_cases_have_multiple_turns(self):
        self.assertGreaterEqual(len(CONVERSATIONS), 2)
        for scenario in CONVERSATIONS:
            self.assertGreaterEqual(len(scenario["turns"]), 3)
            self.assertTrue(all(turn.get("checks") for turn in scenario["turns"]))


if __name__ == "__main__":
    unittest.main()
