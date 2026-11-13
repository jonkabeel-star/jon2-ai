from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_model import build_evaluation_prompt, load_prompts


def test_build_evaluation_prompt_preserves_ordered_multi_turn_context():
    item = {
        "history": [
            {"role": "user", "content": "ما هي الطاقة الشمسية؟"},
            {"role": "assistant", "content": "طاقة نحصل عليها من ضوء الشمس."},
        ],
        "prompt": "إزاي نخزن الكهرباء؟",
    }
    prompt = build_evaluation_prompt(item)
    assert prompt.index("المستخدم: ما هي") < prompt.index("Jon2: طاقة")
    assert prompt.endswith("المستخدم: إزاي نخزن الكهرباء؟\nJon2:")


def test_load_prompts_accepts_optional_history(tmp_path):
    path = tmp_path / "prompts.jsonl"
    path.write_text(json.dumps({
        "id": "multi_01",
        "history": [{"role": "user", "content": "أهلًا"}],
        "prompt": "فاكر أنا قلت إيه؟",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    prompts = load_prompts(path)
    assert prompts[0]["history"] == [{"role": "user", "content": "أهلًا"}]


def test_load_prompts_rejects_invalid_history_role(tmp_path):
    path = tmp_path / "prompts.jsonl"
    path.write_text(json.dumps({
        "id": "bad_01",
        "history": [{"role": "system", "content": "غير مسموح"}],
        "prompt": "سؤال",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        load_prompts(path)
    except ValueError as error:
        assert "invalid history role" in str(error)
    else:
        raise AssertionError("invalid history role must be rejected")
