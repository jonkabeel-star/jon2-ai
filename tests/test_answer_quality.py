import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai_engine"))

from answer_quality import diagnose_answer, validate_generated_answer


class ArabicAnswerQualityTests(unittest.TestCase):
    def test_rejects_observed_fragmented_arabic_reply_one(self):
        answer = "ال وط الر الد الضح الط ولا الب الاسة الهدف الًا."
        self.assertFalse(validate_generated_answer(answer))
        self.assertIn(
            "fragmented_arabic_word_sequence",
            diagnose_answer(answer)["surface_warnings"],
        )

    def test_rejects_observed_fragmented_arabic_reply_two(self):
        answer = "وأق الذلك ال الط المصف الب الاسم الد والح الر والجه والت والن والق والإني والع والأعديل المشخص والر الأو والكث والتوقبل والخل والولا."
        self.assertFalse(validate_generated_answer(answer))

    def test_keeps_short_natural_arabic_answers(self):
        self.assertTrue(validate_generated_answer("نعم، بالتأكيد."))
        self.assertTrue(validate_generated_answer("لا، ليس الآن."))

    def test_keeps_a_coherent_longer_arabic_sentence(self):
        answer = "يمكنك تنظيم يومك بكتابة المهام أولًا، ثم اختيار الأهم وتخصيص وقت مناسب لكل مهمة."
        self.assertTrue(validate_generated_answer(answer))

    def test_diagnostics_never_claim_semantic_understanding(self):
        report = diagnose_answer("القاهرة عاصمة مصر.")
        self.assertTrue(report["human_semantic_review_required"])


if __name__ == "__main__":
    unittest.main()
