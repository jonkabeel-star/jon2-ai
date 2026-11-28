"""Small deterministic Arabic-first response layer for Jon2 Lite.

This is a safe starter, not a trained language model. It handles a few
high-confidence conversational intents and clearly marks the future model
integration seam. Unknown requests are not answered with fabricated facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class BrainReply:
    text: str
    intent: str
    language_style: str
    model_used: bool = False


ModelAdapter = Callable[[str, str], str]


def detect_style(text: str) -> str:
    """Choose Egyptian Arabic when common Egyptian markers are present."""
    egyptian_markers = (
        "إزيك", "ازيك", "عامل ايه", "عاملة ايه", "عايز", "عاوز",
        "محتاج", "ليه", "إيه", "ايه", "مش", "بقى", "دلوقتي",
    )
    return "egyptian" if any(marker in text for marker in egyptian_markers) else "msa"


def _rule_reply(text: str, style: str) -> Optional[BrainReply]:
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return BrainReply("اكتب رسالتك أولًا.", "empty", style)

    greetings = ("مرحبا", "مرحباً", "السلام عليكم", "صباح الخير", "مساء الخير", "أهلا", "اهلا", "هاي", "hello", "hi")
    if any(token in normalized for token in greetings):
        answer = "أهلًا بك! كيف أستطيع مساعدتك؟" if style == "msa" else "أهلاً بيك! أقدر أساعدك في إيه؟"
        return BrainReply(answer, "greeting", style)

    if any(token in normalized for token in ("إزيك", "ازيك", "كيف حالك", "عامل ايه", "عاملة ايه")):
        answer = "أنا بخير، شكرًا لسؤالك. كيف حالك؟" if style == "msa" else "تمام، شكرًا لسؤالك! إنت عامل إيه؟"
        return BrainReply(answer, "wellbeing", style)

    if any(token in normalized for token in ("شكرا", "شكرًا", "متشكر", "تسلم", "thank you", "thanks")):
        answer = "على الرحب والسعة!" if style == "msa" else "العفو، تحت أمرك!"
        return BrainReply(answer, "thanks", style)

    if any(token in normalized for token in ("من أنت", "انت مين", "إنت مين", "ما هو jon2", "ما هو جون")):
        answer = (
            "أنا Jon2 Lite، نواة تجريبية خفيفة. أتعامل حاليًا مع بعض العبارات بقواعد بسيطة، "
            "ولم يتم توصيل نموذج لغوي مدرّب بي بعد."
            if style == "msa" else
            "أنا Jon2 Lite، نسخة تجريبية خفيفة. بفهم حاليًا شوية عبارات بقواعد بسيطة، "
            "ولسه مفيش نموذج لغوي متوصل بيا."
        )
        return BrainReply(answer, "identity", style)

    return None


def generate_with_model(prompt: str, language_style: str, adapter: Optional[ModelAdapter] = None) -> str:
    """Future integration seam. No provider, API key, or model is configured.

    A future local model adapter can be injected by the application after
    quality, licensing, and resource checks. This function never calls a
    remote service by itself.
    """
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
        "لم أفهم الطلب بدقة بعد. هذه النسخة لا تحتوي على نموذج لغوي متصل؛ جرّب تحية أو سؤالًا بسيطًا."
        if style == "msa" else
        "لسه مش قادر أفهم الطلب ده بدقة. النسخة دي مفيهاش نموذج لغوي متوصل؛ جرّب تحية أو سؤال بسيط."
    )
    return BrainReply(fallback, "unsupported", style)
