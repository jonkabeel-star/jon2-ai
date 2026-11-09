"""Fail-closed tests for semantic judging and training authorization."""
from __future__ import annotations
import json, unittest
from pathlib import Path
from unittest.mock import patch
from semantic_evaluator import judge_answer
from training_gate import prepare

class SemanticAndTrainingTests(unittest.TestCase):
    def test_semantic_judge_accepts_only_strict_positive_json(self):
        data={"semantically_correct":True,"answers_question":True,"contains_material_error":False,"contains_unsupported_claim":False,"dialect_appropriate":True,"confidence":0.91,"rationale":"صحيح","issues":[]}
        with patch("semantic_evaluator._chat",return_value=json.dumps(data)):
            result=judge_answer({"test_id":"x","reference_answer":"مرجع","prompt":"سؤال"},"جواب")
        self.assertTrue(result["passed"])
    def test_semantic_judge_rejects_wrong_answer(self):
        data={"semantically_correct":False,"answers_question":True,"contains_material_error":True,"contains_unsupported_claim":False,"dialect_appropriate":True,"confidence":0.99,"rationale":"خطأ","issues":["خطأ"]}
        with patch("semantic_evaluator._chat",return_value=json.dumps(data)):
            result=judge_answer({"test_id":"x","reference_answer":"مرجع"},"خاطئ")
        self.assertFalse(result["passed"])
    def test_semantic_judge_requires_reference(self):
        with self.assertRaises(ValueError): judge_answer({"test_id":"x"},"جواب")
    def test_training_never_authorizes_when_preflight_blocked(self):
        fake={"readiness":{"ready":False,"blockers":["insufficient_tokens_per_parameter"]}}
        with patch("training_gate.build_report",return_value=fake),patch("torch.cuda.is_available",return_value=False):
            result=prepare(Path("."),Path("approvals.json"),"arabic_30m",Path("not-created.pt"))
        self.assertFalse(result["authorized_to_train"])
        self.assertFalse(result["training_started"])

if __name__=="__main__": unittest.main()
