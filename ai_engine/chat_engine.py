"""Runtime for the original Jon2 language model.

No pretrained third-party model or hosted AI API is loaded. The model must
first be trained and saved as a Jon2 checkpoint.
"""
import os
import re
from pathlib import Path

from jon2_core import generate, load_model

CHECKPOINT_PATH = Path(
    os.getenv(
        "JON2_CHECKPOINT",
        str(Path(__file__).resolve().parent / "checkpoints" / "jon2-small.pt"),
    )
)

_model = None
_tokenizer = None
_device = None

# Arabic text and ordinary punctuation only. This is a conservative output
# sanity check, not a proof that an answer is factually correct.
_ALLOWED_ANSWER = re.compile(
    r"^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»\"'\-]+$"
)
_ARABIC_LETTERS = re.compile(r"[\u0621-\u064A\u066E-\u06D3]")


def validate_generated_answer(answer: str) -> bool:
    """Reject empty, corrupted, mixed-script, or obvious looping output."""
    if not isinstance(answer, str):
        return False
    answer = answer.strip()
    if len(answer) < 2 or len(answer) > 4000:
        return False
    if not _ALLOWED_ANSWER.fullmatch(answer):
        return False

    visible = [char for char in answer if not char.isspace()]
    arabic_count = len(_ARABIC_LETTERS.findall(answer))
    if arabic_count / max(1, len(visible)) < 0.70:
        return False

    if re.search(r"(.)\1{3,}", answer):
        return False
    if re.search(r"(.{2,8})\1{2,}", answer):
        return False

    words = answer.split()
    if len(words) >= 8:
        for size in (1, 2, 3):
            if any(
                words[index:index + size] == words[index + size:index + 2 * size]
                == words[index + 2 * size:index + 3 * size]
                for index in range(len(words) - 3 * size + 1)
            ):
                return False
    return True


def model_is_ready() -> bool:
    return _model is not None and _tokenizer is not None


def checkpoint_is_available() -> bool:
    return CHECKPOINT_PATH.is_file()


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


def build_conversation_prompt(message: str, history=None) -> str:
    """Build a bounded Arabic dialogue prompt from validated recent turns."""
    turns = []
    for item in (history or [])[-8:]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        label = "المستخدم" if role == "user" else "Jon2"
        turns.append(f"{label}: {content}")
    turns.append(f"المستخدم: {message.strip()}")
    return "\n".join(turns) + "\nJon2:"


def generate_reply(message: str, history=None) -> str:
    if not message or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")

    load_runtime()
    prompt = build_conversation_prompt(message, history)
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
