from pathlib import Path
import sys

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))
from evaluate_model import load_prompts


def test_egyptian_arabic_evaluation_set_is_valid_and_unique():
    prompts_path = ENGINE_DIR / "evaluation" / "prompts_egyptian_ar.jsonl"
    prompts = load_prompts(prompts_path)
    assert len(prompts) == 30
    ids = [item["id"] for item in prompts]
    assert len(ids) == len(set(ids))
    assert all(item["prompt"].strip() for item in prompts)


def test_egyptian_arabic_evaluation_covers_dialect_and_uncertainty():
    prompts_path = ENGINE_DIR / "evaluation" / "prompts_egyptian_ar.jsonl"
    prompts = load_prompts(prompts_path)
    text = "\n".join(item["prompt"] for item in prompts)
    assert "بالمصري الطبيعي" in text
    assert "هل الجملة واضحة" in text
    assert "مش متأكد" in text
