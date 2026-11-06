"""Runtime for the original Jon2 language model.

No pretrained third-party model or hosted AI API is loaded. The model must
first be trained and saved as a Jon2 checkpoint. Heavy PyTorch/model imports
are deliberately lazy so the API health service can start on small hosts.
"""
import os
from pathlib import Path

from answer_quality import validate_generated_answer

CHECKPOINT_PATH = Path(
    os.getenv(
        "JON2_CHECKPOINT",
        str(Path(__file__).resolve().parent / "checkpoints" / "jon2-small.pt"),
    )
)

_model = None
_tokenizer = None
_device = None


def model_is_ready() -> bool:
    return _model is not None and _tokenizer is not None


def checkpoint_is_available() -> bool:
    return CHECKPOINT_PATH.is_file()


def load_model(checkpoint_path: str):
    """Import the PyTorch model runtime only when a real checkpoint exists."""
    from jon2_core import load_model as load_jon2_model
    return load_jon2_model(checkpoint_path)


def generate(*args, **kwargs):
    """Import generation code only when a loaded model is actually used."""
    from jon2_core import generate as generate_jon2
    return generate_jon2(*args, **kwargs)


def load_runtime() -> None:
    global _model, _tokenizer, _device
    if model_is_ready():
        return
    if not checkpoint_is_available():
        raise FileNotFoundError(
            "لم يتم تدريب نموذج Jon2 الأصلي بعد. ملف الأوزان غير موجود: "
            f"{CHECKPOINT_PATH}"
        )
    _model, _tokenizer, _device = load_model(str(CHECKPOINT_PATH))


def build_conversation_prompt(message: str, history=None, memories=None) -> str:
    """Build a compact prompt that fits the original model's short context."""
    sections = []
    relevant = []
    for item in (memories or [])[:2]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            label = "المستخدم" if role == "user" else "Jon2"
            relevant.append(f"{label}: {content.strip()[-90:]}")
    if relevant:
        sections.append("ذاكرة سابقة:\n" + "\n".join(relevant))
    turns = []
    for item in (history or [])[-4:]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        label = "المستخدم" if role == "user" else "Jon2"
        turns.append(f"{label}: {content[-90:]}")
    turns.append(f"المستخدم: {message.strip()[-220:]}")
    sections.append("\n".join(turns) + "\nJon2:")
    return "\n".join(sections)


def generate_reply(message: str, history=None, memories=None) -> str:
    if not message or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")

    load_runtime()
    prompt = build_conversation_prompt(message, history, memories)
    full_text = generate(
        _model,
        _tokenizer,
        prompt,
        _device,
        max_new_chars=int(os.getenv("JON2_MAX_NEW_CHARS", "400")),
        temperature=float(os.getenv("JON2_TEMPERATURE", "0.8")),
        stop_sequences=["المستخدم:"],
    )
    answer = full_text[len(prompt):].strip()
    if not answer:
        raise RuntimeError("لم ينتج نموذج Jon2 إجابة.")
    if not validate_generated_answer(answer):
        raise RuntimeError(
            "رفض Jon2 عرض الإجابة لأن ناتج النموذج يحتوي على رموز أو نص مشوّه. "
            "يلزم تحسين النموذج وإعادة تقييمه قبل الاستخدام."
        )
    return answer
