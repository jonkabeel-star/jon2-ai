"""Adversarial and context-consistency tests for the evaluation engine."""
import unittest

from jon2_lite.brain import respond
from jon2_lite.evaluation import EvaluationCase, evaluate_batch, evaluate_reply


class EvaluationEngineTests(unittest.TestCase):
    def test_msa_and_egyptian_compound_reasoning_contracts(self):
        cases = (
            EvaluationCase(
                name="msa_plan",
                prompt="كيف أتعلم البرمجة؟",
                expected_intent="step_by_step_plan",
                required_terms=("البرمجة", "1.", "5."),
            ),
            EvaluationCase(
                name="egyptian_plan",
                prompt="ازاي أبدأ أتعلم التصميم؟",
                expected_intent="step_by_step_plan",
                required_terms=("التصميم", "نقدر نمشي"),
            ),
            EvaluationCase(
                name="arabic_arithmetic_precedence",
                prompt="احسب (١٢ + ٣) * ٢",
                expected_intent="arithmetic",
                required_terms=("30",),
            ),
            EvaluationCase(
                name="ambiguous_comparison",
                prompt="أيهما أفضل؟",
                expected_intent="clarification_needed",
                must_abstain=True,
            ),
        )
        report = evaluate_batch(cases, respond)
        self.assertEqual(report["passed"], 4)
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["score"], 100.0)

    def test_unsupported_fact_question_must_abstain(self):
        reply = respond("ما عاصمة كوكب زحل؟")
        result = evaluate_reply("ما عاصمة كوكب زحل؟", reply, must_abstain=True)
        self.assertTrue(result.passed, result.failures)
        self.assertFalse(reply.model_used)

    def test_saved_fact_response_must_match_current_fact(self):
        facts = [{"fact_key": "المجال", "fact_value": "تحليل البيانات"}]
        reply = respond("ماذا تعرف عني؟", facts=facts)
        result = evaluate_reply(
            "ماذا تعرف عني؟", reply, expected_intent="memory_facts",
            required_terms=("تحليل البيانات",), facts=facts,
        )
        self.assertTrue(result.passed, result.failures)

    def test_stale_or_wrong_memory_value_is_detected(self):
        facts = [{"fact_key": "المجال", "fact_value": "تحليل البيانات"}]
        wrong_reply = respond("ماذا تعرف عني؟", facts=[
            {"fact_key": "المجال", "fact_value": "الطب"}
        ])
        result = evaluate_reply("ماذا تعرف عني؟", wrong_reply, facts=facts)
        self.assertFalse(result.passed)
        self.assertIn("context_consistency", result.failures)

    def test_conflicting_duplicate_fact_keys_are_flagged(self):
        facts = [
            {"fact_key": "المجال", "fact_value": "البرمجة"},
            {"fact_key": "المجال", "fact_value": "التصميم"},
        ]
        reply = respond("ماذا تعرف عني؟", facts=facts)
        result = evaluate_reply("ماذا تعرف عني؟", reply, facts=facts)
        self.assertFalse(result.checks["context_consistency"])

    def test_history_context_must_be_reflected_in_recall(self):
        history = [
            {"role": "user", "content": "أريد تعلم البرمجة"},
            {"role": "assistant", "content": "ابدأ بالأساسيات"},
            {"role": "user", "content": "أهتم أيضًا بتحليل البيانات"},
        ]
        reply = respond("ماذا تحدثنا عنه؟", history=history)
        result = evaluate_reply(
            "ماذا تحدثنا عنه؟", reply, expected_intent="memory_history",
            facts=(), history=history,
        )
        self.assertTrue(result.passed, result.failures)

    def test_plan_must_not_ignore_explicit_session_goal(self):
        history = [{"role": "user", "content": "عايز أتعلم البرمجة"}]
        reply = respond("ازاي أبدأ؟", history=history)
        result = evaluate_reply("ازاي أبدأ؟", reply, history=history)
        self.assertTrue(result.checks["context_consistency"])

    def test_model_usage_is_not_claimed_for_abstentions(self):
        reply = respond("ما نتيجة تجربة علمية غير محددة؟")
        result = evaluate_reply("ما نتيجة تجربة علمية غير محددة؟", reply, must_abstain=True)
        self.assertTrue(result.checks["no_unverified_model_claim"])
        self.assertFalse(reply.model_used)

    def test_empty_batch_is_defined_and_does_not_crash(self):
        report = evaluate_batch((), respond)
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["score"], 100.0)


if __name__ == "__main__":
    unittest.main()
