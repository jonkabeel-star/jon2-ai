"""Regression tests for Arabic style, contextual memory, fact lifecycle and session isolation."""
import sqlite3
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



    def test_reasoning_arithmetic_msa_and_egyptian_digits(self):
        msa = respond("احسب 12 + 3 * 2")
        egy = respond("كام ١٢ + ٣؟")
        self.assertEqual(msa.intent, "arithmetic")
        self.assertIn("18", msa.text)
        self.assertEqual(egy.intent, "arithmetic")
        self.assertIn("15", egy.text)

    def test_reasoning_division_by_zero_abstains(self):
        reply = respond("احسب 8 / 0")
        self.assertNotEqual(reply.intent, "arithmetic")
        self.assertFalse(reply.model_used)

    def test_reasoning_builds_explicit_plan_in_msa(self):
        reply = respond("كيف أتعلم البرمجة؟")
        self.assertEqual(reply.intent, "step_by_step_plan")
        self.assertIn("1.", reply.text)
        self.assertIn("البرمجة", reply.text)
        self.assertIn("5.", reply.text)

    def test_reasoning_builds_plan_in_egyptian(self):
        reply = respond("ازاي أبدأ أتعلم التصميم؟")
        self.assertEqual(reply.intent, "step_by_step_plan")
        self.assertIn("نقدر نمشي", reply.text)
        self.assertIn("التصميم", reply.text)

    def test_reasoning_uses_session_history_and_saved_facts(self):
        history = [{"role": "user", "content": "عايز أتعلم البرمجة"}]
        from_history = respond("ازاي أبدأ؟", history=history)
        facts = [{"fact_key": "المجال", "fact_value": "تحليل البيانات"}]
        from_fact = respond("كيف أبدأ؟", facts=facts)
        self.assertEqual(from_history.intent, "step_by_step_plan")
        self.assertIn("البرمجة", from_history.text)
        self.assertEqual(from_fact.intent, "step_by_step_plan")
        self.assertIn("تحليل البيانات", from_fact.text)

    def test_reasoning_asks_for_missing_goal_or_comparison_options(self):
        missing_goal = respond("كيف أبدأ؟")
        missing_options = respond("أيهما أفضل؟")
        self.assertEqual(missing_goal.intent, "clarification_needed")
        self.assertEqual(missing_options.intent, "clarification_needed")
        self.assertFalse(missing_goal.model_used)


class LiteMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.memory = LiteMemory(self.db_path)

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

    def test_facts_are_session_scoped_and_can_be_updated_and_forgotten(self):
        self.memory.save_fact("المجال", "البرمجة", "s1")
        self.memory.save_fact("المجال", "الذكاء الاصطناعي", "s1")
        self.memory.save_fact("المجال", "التصميم", "s2")
        self.assertEqual(self.memory.facts("s1")[0]["fact_value"], "الذكاء الاصطناعي")
        self.assertEqual(self.memory.facts("s2")[0]["fact_value"], "التصميم")
        self.assertTrue(self.memory.delete_fact("المجال", "s1"))
        self.assertEqual(self.memory.facts("s1"), [])
        self.assertEqual(self.memory.facts("s2")[0]["fact_value"], "التصميم")
        self.assertFalse(self.memory.delete_fact("المجال", "s1"))

    def test_session_clear_and_message_validation(self):
        self.memory.add_message("s1", "user", "رسالة")
        self.assertEqual(self.memory.clear_session("s1"), 1)
        self.assertEqual(self.memory.history("s1"), [])
        with self.assertRaises(ValueError):
            self.memory.add_message("s1", "system", "غير مسموح")

    def test_legacy_global_facts_migrate_without_loss(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_path) as db:
            db.execute("CREATE TABLE facts (fact_key TEXT PRIMARY KEY, fact_value TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("INSERT INTO facts VALUES ('name', 'Jon2', '2026-01-01T00:00:00Z')")
        migrated = LiteMemory(legacy_path)
        self.assertEqual(migrated.facts("")[0]["fact_value"], "Jon2")
        self.assertEqual(migrated.facts("s1"), [])


if __name__ == "__main__":
    unittest.main()
