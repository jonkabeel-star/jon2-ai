"""Runtime for the original Jon2 language model.

This module intentionally does not load Qwen, GPT, or any hosted AI API.
A trained Jon2 checkpoint must exist before chat can be used.
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


def load_runtime() -> None:
    global _model, _tokenizer, _device
    if model_is_ready():
        return
    if not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(
            "لم يتم تدريب نموذج Jon2 الأصلي بعد. ملف الأوزان المطلوب غير موجود: "
            f"{CHECKPOINT_PATH}"
        )
    _model, _tokenizer, _device = load_model(str(CHECKPOINT_PATH))


def generate_reply(message: str) -> str:
    if not message or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")
    load_runtime()
    full_text = generate(
        _model,
        _tokenizer,
        message.strip(),
        _device,
        max_new_chars=int(os.getenv("JON2_MAX_NEW_CHARS", "400")),
        temperature=float(os.getenv("JON2_TEMPERATURE", "0.8")),
    )
    answer = full_text[len(message.strip()):].strip()
    if not answer:
        raise RuntimeError("لم ينتج نموذج Jon2 إجابة.")
    return answer
