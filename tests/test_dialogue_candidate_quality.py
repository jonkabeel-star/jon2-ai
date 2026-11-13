"""Structural and editorial guardrails for the quarantined Arabic dialogue candidates.

These checks do not certify factual correctness or replace human linguistic review.
"""
import json
import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "ai_engine" / "data_candidates" / "jon2_ar_dialogue_batch_500_v1.jsonl"
ARABIC = re.compile(r"[\u0600-\u06ff]")


class DialogueCandidateQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [
            json.loads(line)
            for line in DATASET.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_batch_has_expected_size_and_topic_balance(self):
        self.assertEqual(len(self.records), 500)
        counts = Counter(record["topic"] for record in self.records)
        self.assertEqual(len(counts), 20)
        self.assertEqual(set(counts.values()), {25})

    def test_ids_and_prompts_are_unique(self):
        self.assertEqual(len({record["id"] for record in self.records}), 500)
        prompts = [record["messages"][0]["content"] for record in self.records]
        self.assertEqual(len(set(prompts)), 500)

    def test_candidate_records_are_never_training_eligible(self):
        for record in self.records:
            self.assertEqual(record["review_status"], "candidate_only")
            self.assertIs(record["training_eligible"], False)

    def test_messages_are_nonempty_and_arabic(self):
        for record in self.records:
            self.assertEqual([m["role"] for m in record["messages"]], ["user", "assistant"])
            for message in record["messages"]:
                self.assertTrue(message["content"].strip())
                self.assertRegex(message["content"], ARABIC)

    def test_no_exact_duplicate_answers(self):
        answers = [record["messages"][1]["content"] for record in self.records]
        self.assertEqual(len(set(answers)), len(answers))

    def test_removed_repeated_topic_preface_and_bad_punctuation(self):
        for record in self.records:
            answer = record["messages"][1]["content"]
            self.assertFalse(answer.startswith("في موضوع "))
            self.assertNotIn("..", answer)
            self.assertNotIn("،،", answer)

    def test_first_step_answers_use_natural_colon_construction(self):
        for record in self.records:
            if record["messages"][0]["content"].startswith("ما أول خطوة عملية"):
                answer = record["messages"][1]["content"]
                self.assertTrue(answer.startswith("أول خطوة عملية: "))
                self.assertNotIn("هي ابدأ", answer)

    def test_all_examples_remain_in_candidate_directory(self):
        self.assertEqual(DATASET.parent.name, "data_candidates")
        self.assertNotIn("training_data", DATASET.parts)

    def test_generic_question_families_have_topic_specific_answers(self):
        families = {
            "beginner": "هل يمكن تعلم",
            "overdoing": "كيف أتجنب المبالغة",
            "recovery": "ماذا أفعل إذا لم تنجح أول محاولة",
        }
        for family, prefix in families.items():
            selected = [
                record for record in self.records
                if record["messages"][0]["content"].startswith(prefix)
            ]
            self.assertEqual(len(selected), 20, family)
            answers = [record["messages"][1]["content"] for record in selected]
            self.assertEqual(len(set(answers)), 20, family)

        all_answers = [record["messages"][1]["content"] for record in self.records]
        forbidden_boilerplate = (
            "لا تحتاج إلى خبرة سابقة. ابدأ بالأساسيات",
            "اترك وقتًا للطوارئ والراحة، ولا تحوّل الوسيلة إلى هدف",
            "لا تكرر المحاولة نفسها تلقائيًا",
        )
        for answer in all_answers:
            for phrase in forbidden_boilerplate:
                self.assertNotIn(phrase, answer)


if __name__ == "__main__":
    unittest.main()
