import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai_engine"))

from answer_quality import diagnose_answer, validate_generated_answer


def test_rejects_observed_fragmented_arabic_reply_one():
    answer = "ال وط الر الد الضح الط ولا الب الاسة الهدف الًا."
    assert validate_generated_answer(answer) is False
    assert "fragmented_arabic_word_sequence" in diagnose_answer(answer)["surface_warnings"]


def test_rejects_observed_fragmented_arabic_reply_two():
    answer = "وأق الذلك ال الط المصف الب الاسم الد والح الر والجه والت والن والق والإني والع والأعديل المشخص والر الأو والكث والتوقبل والخل والولا."
    assert validate_generated_answer(answer) is False


def test_keeps_short_natural_arabic_answers():
    assert validate_generated_answer("نعم، بالتأكيد.") is True
    assert validate_generated_answer("لا، ليس الآن.") is True


def test_keeps_a_coherent_longer_arabic_sentence():
    answer = "يمكنك تنظيم يومك بكتابة المهام أولًا، ثم اختيار الأهم وتخصيص وقت مناسب لكل مهمة."
    assert validate_generated_answer(answer) is True


def test_diagnostics_never_claim_semantic_understanding():
    report = diagnose_answer("القاهرة عاصمة مصر.")
    assert report["human_semantic_review_required"] is True
