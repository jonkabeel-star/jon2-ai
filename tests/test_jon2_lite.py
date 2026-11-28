"""Regression tests for Arabic and Egyptian Jon2 Lite behavior and SQLite memory."""
import tempfile
import unittest
from pathlib import Path

from jon2_lite.brain import detect_style, respond
from jon2_lite.memory import LiteMemory


class ArabicBrainTests(unittest.TestCase):
    def test_msa_greetings(self):
        for prompt in ("مرحبا", "السلام عليكم", "صباح الخير", "أهلاً"):
            with self.subTest(prompt=prompt):
                self.assertEqual(respond(prompt).intent, "greeting")
                self.assertEqual(respond(prompt).language_style, "msa")

    def test_egyptian_greetings_and_spelling_variants(self):
        for prompt in ("ازيك", "إزيك", "عامل ايه", "عامل إيه"):
            with self.subTest(prompt=prompt):
                reply = respond(prompt)
                self.assertEqual(reply.intent, "wellbeing")
                self.assertEqual(reply.language_style, "egyptian")

    def test_thanks_in_both_styles(self):
        self.assertEqual(respond("شكراً").intent, "thanks")
        self.assertEqual(respond("تسلم يا صاحبي").intent, "thanks")
        self.assertEqual(respond("تسلم يا صاحبي").language_style, "egyptian")

    def test_identity_and_capabilities(self):
        self.assertEqual(respond("من أنت؟").intent, "identity")
        self.assertEqual(respond("إنت مين؟").intent, "identity")
        self.assertEqual(respond("ماذا تستطيع أن تفعل؟").intent, "capabilities")
        self.assertEqual(respond("بتقدر تعمل ايه؟").intent, "capabilities")

    def test_model_status_is_honest(self):
        for prompt in ("هل أنت ذكاء اصطناعي؟", "هل أنت نموذج؟"):
            with self.subTest(prompt=prompt):
                reply = respond(prompt)
                self.assertEqual(reply.intent, "model_status")
                self.assertFalse(reply.model_used)
                self.assertIn("مدرّب", reply.text)

    def test_explanation_and_unknown_questions_do_not_hallucinate(self):
        self.assertEqual(respond("اشرح لي الذكاء الاصطناعي").intent, "explanation_request")
        for prompt in ("لماذا السماء زرقاء؟", "كيف أتعلم البرمجة؟", "فين أقرب مكتبة؟", "What is AI?"):
            with self.subTest(prompt=prompt):
                reply = respond(prompt)
                self.assertIn(reply.intent, {"unsupported_question", "unsupported"})
                self.assertFalse(reply.model_used)

    def test_empty_and_whitespace(self):
        self.assertEqual(respond("").intent, "empty")
        self.assertEqual(respond("   ").intent, "empty")

    def test_style_detection(self):
        self.assertEqual(detect_style("عايز أتعلم"), "egyptian")
        self.assertEqual(detect_style("كيف أتعلم؟"), "msa")

    def test_local_adapter_is_explicitly_injected(self):
        reply = respond("اكتب قصيدة", lambda prompt, style: "نص تجريبي")
        self.assertEqual(reply.text, "نص تجريبي")
        self.assertEqual(reply.intent, "model")
        self.assertTrue(reply.model_used)


class LiteMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.memory = LiteMemory(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_message_round_trip_and_session_isolation(self):
        self.memory.add_message("session-a", "user", "مرحبا")
        self.memory.add_message("session-a", "assistant", "أهلًا")
        self.memory.add_message("session-b", "user", "أهلا")
        history = self.memory.history("session-a")
        self.assertEqual([m["role"] for m in history], ["user", "assistant"])
        self.assertEqual(len(self.memory.history("session-b")), 1)

    def test_history_limit_is_bounded(self):
        for i in range(5):
            self.memory.add_message("s", "user", str(i))
        self.assertEqual(len(self.memory.history("s", limit=2)), 2)

    def test_invalid_role_rejected(self):
        with self.assertRaises(ValueError):
            self.memory.add_message("s", "system", "blocked")

    def test_facts_upsert_and_validation(self):
        self.memory.save_fact("language", "Arabic")
        self.memory.save_fact("language", "Arabic and Egyptian")
        facts = self.memory.facts()
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["fact_value"], "Arabic and Egyptian")
        with self.assertRaises(ValueError):
            self.memory.save_fact(" ", "value")


if __name__ == "__main__":
    unittest.main()
