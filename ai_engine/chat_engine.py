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


def build_conversation_prompt(message: str, history=None, memories=None, tokenizer=None, context=None, knowledge_context=None) -> str:
    """Build a lossless conversation prompt with optional retrieved reference context."""
    question = str(message).strip()
    if not question:
        raise ValueError("اكتب رسالتك أولًا.")

    memory_items = []
    for item in (memories or [])[:2]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            label = "المستخدم" if role == "user" else "Jon2"
            memory_items.append(f"{label}: {content.strip()[-90:]}")

    reference_context = str(knowledge_context or "").strip()
    turns = []
    for item in (history or [])[-4:]:
        role = item.get("role") if isinstance(item, dict) else None
        content = item.get("content") if isinstance(item, dict) else None
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        content = content.strip()
        if content:
            label = "المستخدم" if role == "user" else "Jon2"
            turns.append(f"{label}: {content[-90:]}")

    # Reserve the final token for the model's answer marker. Remove older
    # context first, but never silently truncate the user's current question:
    # dropping its ending can reverse or destroy the meaning of Arabic requests.
    token_limit = max(8, int(context or getattr(_model, "context", 128)))
    while True:
        sections = []
        if reference_context:
            sections.append(
                "معلومات مرجعية مسترجعة للاسترشاد والتحقق، وليست إجابة جاهزة؛ "
                "أجب بصياغتك أنت ولا تنسخ النص حرفيًا:\n" + reference_context
            )
        if memory_items:
            sections.append("ذاكرة سابقة:\n" + "\n".join(memory_items))
        dialogue = list(turns) + [f"المستخدم: {question}\nJon2:"]
        sections.append("\n".join(dialogue))
        prompt = "\n".join(sections)
        if tokenizer is None or len(tokenizer.encode(prompt)) <= token_limit - 1:
            return prompt
        if turns:
            turns.pop(0)
            continue
        if memory_items:
            memory_items.pop(0)
            continue
        if reference_context:
            raise ValueError(
                "المعلومات المرجعية والسؤال لا يتسعان داخل نافذة سياق نموذج Jon2؛ "
                "لن يتم حذف السؤال أو اختصاره."
            )
        raise ValueError(
            "سؤال المستخدم أطول من نافذة سياق نموذج Jon2؛ "
            "لن يتم اختصاره حتى لا يتغير معناه."
        )


def generate_reply(message: str, history=None, memories=None, knowledge_context=None) -> str:
    if not message or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")

    load_runtime()
    prompt = build_conversation_prompt(
        message, history, memories,
        tokenizer=_tokenizer if callable(getattr(_tokenizer, "encode", None)) else None,
        context=getattr(_model, "context", 128),
        knowledge_context=knowledge_context,
    )
    full_text = generate(
        _model,
        _tokenizer,
        prompt,
        _device,
        max_new_chars=int(os.getenv("JON2_MAX_NEW_CHARS", "400")),
        # Greedy decoding is more stable for this small from-scratch model.
        # Sampling can turn an already weak language model into visibly broken Arabic.
        temperature=float(os.getenv("JON2_TEMPERATURE", "1.0")),
        stop_sequences=["المستخدم:"],
        do_sample=False,
        repetition_penalty=1.10,
        no_repeat_ngram_size=3,
        top_k=0,
    )
    answer = full_text[len(prompt):].strip()
    if not answer:
        raise RuntimeError("لم ينتج نموذج Jon2 إجابة.")
    # Experimental mode must never bypass basic output-integrity checks.
    # This catches malformed characters and obvious repetition, not semantic quality.
    if not validate_generated_answer(answer):
        raise RuntimeError(
            "رفض Jon2 عرض الإجابة لأن ناتج النموذج فشل فحص سلامة النص. "
            "يلزم تحسين بيانات التدريب وإعادة تقييم النموذج."
        )
    return answer
