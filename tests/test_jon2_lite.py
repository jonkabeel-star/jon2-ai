"""Regression tests for Arabic style, contextual memory, fact lifecycle and session isolation."""
import tempfile
import unittest
from pathlib import Path

from jon2_lite.brain import detect_style, respond
from jon2_lite.memory import LiteMemory


class ArabicBrainTests(unittest.TestCase):
    def test_msa_greetings_and_quality(self):
        reply = respond("السلام عليكم")
        self.assertEqual(reply.intent, "greeting")
        self.assertEqual(reply.language_style, "msa")
        self.assertIn("أهلًا بك", reply.text)

    def test_egyptian_greetings_and_quality(self):
        reply = respond("عامل إيه؟")
        self.assertEqual(reply.intent, "wellbeing")
        self.assertEqual(reply.language_style, "egyptian")
        self.assertIn("إنت عامل إيه", reply.text)

    def test_style_and_spelling_variants(self):
        for prompt in ("ازيك", "إزيك", "عامل ايه", "عامل إيه"):
            self.assertEqual(respond(prompt).language_style, "egyptian")
        self.assertEqual(detect_style("كيف أتعلم؟"), "msa")
        self.assertEqual(detect_style("عايز أتعلم"), "egyptian")

    def test_thanks_identity_capabilities(self):
        self.assertEqual(respond("شكراً").intent, "thanks")
        self.assertEqual(respond("تسلم يا صاحبي").intent, "thanks")
        self.assertEqual(respond("من أنت؟").intent, "identity")
        self.assertEqual(respond("بتقدر تعمل ايه؟").intent, "capabilities")

    def test_model_status_is_honest(self):
        reply = respond("هل أنت نموذج؟")
        self.assertEqual(reply.intent, "model_status")
        self.assertFalse(reply.model_used)
        self.assertIn("مدرّب", reply.text)

    def test_unsupported_questions_do_not_hallucinate(self):
        for prompt in ("لماذا السماء زرقاء؟", "كيف أتعلم البرمجة؟", "فين أقرب مكتبة؟", "What is AI?"):
            reply = respond(prompt)
            self.assertIn(reply.intent, {"unsupported_question", "unsupported"})
            self.assertFalse(reply.model_used)

    def test_empty_and_explicit_local_adapter(self):
        self.assertEqual(respond("").intent, "empty")
        reply = respond("اكتب قصيدة", lambda prompt, style: "نص محلي")
        self.assertEqual(reply.text, "نص محلي")
        self.assertTrue(reply.model_used)

    def test_remembers_saved_facts_in_msa_and_egyptian(self):
        facts = [{"fact_key": "اللغة المفضلة", "fact_value": "العربية"}]
        msa = respond("ماذا تعرف عني؟", facts=facts)
        egy = respond("فاكر عني ايه؟", facts=facts)
        self.assertEqual(msa.intent, "memory_facts")
        self.assertIn("العربية", msa.text)
        self.assertEqual(egy.language_style, "egyptian")
        self.assertIn("العربية", egy.text)

    def test_recalls_previous_user_messages(self):
        history = [{"role": "user", "content": "أريد تعلم البرمجة"}]
        reply = respond("ماذا تحدثنا عنه؟", history=history)
        self.assertEqual(reply.intent, "memory_history")
        self.assertIn("أريد تعلم البرمجة", reply.text)

    def test_memory_empty_states_are_clear(self):
        self.assertIn("لا توجد حقائق", respond("ماذا تعرف عني؟").text)
        self.assertIn("لا يوجد سجل", respond("ماذا تحدثنا عنه؟").text)


class LiteMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = LiteMemory(Path(self.temp_dir.name) / "test.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multi_turn_recall_and_session_isolation(self):
        self.memory.add_message("s1", "user", "أريد تعلم البرمجة")
        self.memory.add_message("s1", "assistant", "يمكنك البدء بالأساسيات.")
        self.memory.add_message("s1", "user", "ماذا تحدثنا عنه؟")
        history = self.memory.history("s1")
        reply = respond(history[-1]["content"], history=history[:-1])
        self.assertIn("تعلم البرمجة", reply.text)
        self.assertEqual(self.memory.history("s2"), [])

    def test_fact_update_and_forget(self):
        self.memory.save_fact("المجال", "البرمجة")
        self.memory.save_fact("المجال", "الذكاء الاصطناعي")
        self.assertEqual(self.memory.facts()[0]["fact_value"], "الذكاء الاصطناعي")
        self.assertTrue(self.memory.delete_fact("المجال"))
        self.assertEqual(self.memory.facts(), [])
        self.assertFalse(self.memory.delete_fact("المجال"))

    def test_session_clear_and_message_validation(self):
        self.memory.add_message("s1", "user", "رسالة")
        self.assertEqual(self.memory.clear_session("s1"), 1)
        self.assertEqual(self.memory.history("s1"), [])
        with self.assertRaises(ValueError):
            self.memory.add_message("s1", "system", "غير مسموح")


if __name__ == "__main__":
    unittest.main()
