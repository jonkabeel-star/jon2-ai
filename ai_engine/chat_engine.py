"""Runtime for the original Jon2 language model.

No pretrained third-party model or hosted AI API is loaded. The model must
first be trained and saved as a Jon2 checkpoint.
"""
import os
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


def generate_reply(message: str) -> str:
    if not message or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")

    load_runtime()
    prompt = f"المستخدم: {message.strip()}\nJon2:"
    full_text = generate(
        _model,
        _tokenizer,
        prompt,
        _device,
        max_new_chars=int(os.getenv("JON2_MAX_NEW_CHARS", "400")),
        temperature=float(os.getenv("JON2_TEMPERATURE", "0.8")),
    )
    answer = full_text[len(prompt):].strip()
    if not answer:
        raise RuntimeError("لم ينتج نموذج Jon2 إجابة.")
    return answer
