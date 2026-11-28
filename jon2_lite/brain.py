"""Deterministic Arabic-first response layer for Jon2 Lite.

This is a rule-based starter, not a trained language model. It handles a
small, explicit set of conversational intents and refuses to invent answers.
A local model can later be injected through ModelAdapter.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class BrainReply:
    text: str
    intent: str
    language_style: str
    model_used: bool = False


ModelAdapter = Callable[[str, str], str]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return " ".join(text.split())


def detect_style(text: str) -> str:
    """Choose Egyptian Arabic when common Egyptian markers are present."""
    normalized = _normalize(text)
    markers = (
        "ازيك", "عامل ايه", "عامله ايه", "عايز", "عاوزه", "عاوز",
        "محتاج", "ليه", "ايه", "مش", "بقي", "دلوقتي", "ازاي",
        "اعمل ايه", "فين", "كده", "احنا",
    )
    return "egyptian" if any(marker in normalized for marker in markers) else "msa"


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _rule_reply(text: str, style: str) -> Optional[BrainReply]:
    q = _normalize(text)
    if not q:
        return BrainReply("اكتب رسالتك أولًا.", "empty", style)

    greetings = ("مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", "اهلا", "هاي", "hello", "hi")
    if _contains_any(q, greetings):
        answer = "أهلًا بك! كيف أستطيع مساعدتك؟" if style == "msa" else "أهلاً بيك! أقدر أساعدك في إيه؟"
        return BrainReply(answer, "greeting", style)

    if _contains_any(q, ("ازيك", "كيف حالك", "عامل ايه", "عامله ايه")):
        answer = "أنا بخير، شكرًا لسؤالك. كيف حالك؟" if style == "msa" else "تمام، شكرًا لسؤالك! إنت عامل إيه؟"
        return BrainReply(answer, "wellbeing", style)

    if _contains_any(q, ("شكرا", "متشكر", "تسلم", "thank you", "thanks")):
        answer = "على الرحب والسعة!" if style == "msa" else "العفو، تحت أمرك!"
        return BrainReply(answer, "thanks", style)

    if _contains_any(q, ("من انت", "انت مين", "ما هو jon2", "ما هو جون2")):
        answer = (
            "أنا Jon2 Lite، نواة تجريبية خفيفة. أستخدم حاليًا قواعد محدودة، "
            "ولم يتم توصيل نموذج لغوي مدرّب بي بعد."
            if style == "msa" else
            "أنا Jon2 Lite، نسخة تجريبية خفيفة. بفهم حاليًا شوية طلبات بقواعد بسيطة، "
            "ولسه مفيش نموذج لغوي متوصل بيا."
        )
        return BrainReply(answer, "identity", style)

    if _contains_any(q, ("ماذا تستطيع", "كيف يمكنك مساعدتي", "ما الذي يمكنك فعله", "بتقدر تعمل ايه", "تقدر تساعدني في ايه", "بتعمل ايه")):
        answer = (
            "أستطيع حاليًا الرد على التحيات والشكر والتعريف بنفسي. أما الأسئلة العامة "
            "فتحتاج إلى نموذج لغوي لم يُوصّل بعد."
            if style == "msa" else
            "حاليًا أقدر أرد على التحيات والشكر وأعرّفك بنفسي. الأسئلة العامة محتاجة "
            "نموذج لغوي لسه مش متوصل."
        )
        return BrainReply(answer, "capabilities", style)

    if _contains_any(q, ("هل انت ذكاء اصطناعي", "هل انت نموذج", "انت حقيقي", "انت انسان")):
        answer = (
            "أنا برنامج تجريبي لمعالجة اللغة، لكنني لست نموذجًا لغويًا مدرّبًا حتى الآن."
            if style == "msa" else
            "أنا برنامج تجريبي للتعامل مع الكلام، لكن لسه مش نموذج ذكاء اصطناعي مدرّب."
        )
        return BrainReply(answer, "model_status", style)

    if _contains_any(q, ("ما معنى", "ماذا يعني", "اشرح لي", "اشرحلي", "يعني ايه", "معني")):
        answer = (
            "أحتاج إلى تحديد المصطلح أو إتاحة نموذج لغوي حتى أشرح هذا السؤال بدقة."
            if style == "msa" else
            "حددلي الكلمة أو المصطلح المقصود، لأن الشرح العام لسه محتاج نموذج لغوي."
        )
        return BrainReply(answer, "explanation_request", style)

    if q.endswith("?") or q.endswith("؟") or _contains_any(q, ("لماذا", "كيف", "متى", "اين", "كم", "هل", "ليه", "ازاي", "امتي", "فين")):
        answer = (
            "هذا سؤال يحتاج إلى فهم أوسع أو معلومات موثوقة. لا أملك نموذجًا لغويًا متصلًا الآن، "
            "لذلك لن أخمّن الإجابة."
            if style == "msa" else
            "السؤال ده محتاج فهم أو معلومات أكتر. مفيش نموذج لغوي متوصل بيا دلوقتي، "
            "فعشان كده مش هخمن الإجابة."
        )
        return BrainReply(answer, "unsupported_question", style)

    return None


def generate_with_model(prompt: str, language_style: str, adapter: Optional[ModelAdapter] = None) -> str:
    """Call only an explicitly injected local adapter; never a remote provider."""
    if adapter is None:
        raise RuntimeError("local_model_not_configured")
    return adapter(prompt, language_style)


def respond(text: str, model_adapter: Optional[ModelAdapter] = None) -> BrainReply:
    style = detect_style(text)
    rule_result = _rule_reply(text, style)
    if rule_result is not None:
        return rule_result
    if model_adapter is not None:
        return BrainReply(generate_with_model(text, style, model_adapter), "model", style, True)
    fallback = (
        "لم أفهم الطلب بدقة بعد. هذه النسخة لا تحتوي على نموذج لغوي متصل؛ "
        "جرّب سؤالًا أو طلبًا أوضح."
        if style == "msa" else
        "لسه مش قادر أفهم الطلب ده بدقة. النسخة دي مفيهاش نموذج لغوي متوصل؛ "
        "جرّب توضح طلبك."
    )
    return BrainReply(fallback, "unsupported", style)
