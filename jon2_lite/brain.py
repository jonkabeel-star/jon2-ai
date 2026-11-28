"""Arabic-first deterministic brain with optional local-model injection.

Memory is supplied by the caller; this module never opens a database itself.
This remains a rule-based starter, not a trained language model.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .reasoning import reason


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
    normalized = _normalize(text)
    markers = (
        "ازيك", "عامل ايه", "عامله ايه", "عايز", "عاوزه", "عاوز",
        "محتاج", "ليه", "ايه", "مش", "بقي", "دلوقتي", "ازاي",
        "اعمل ايه", "فين", "كده", "احنا", "يا صاحبي", "يا باشا", "تسلم",
    )
    return "egyptian" if any(marker in normalized for marker in markers) else "msa"


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _style_text(msa: str, egyptian: str, style: str) -> str:
    return egyptian if style == "egyptian" else msa


def _memory_reply(
    normalized: str,
    style: str,
    history: Sequence[dict],
    facts: Sequence[dict],
) -> Optional[BrainReply]:
    asks_facts = _contains_any(normalized, (
        "ماذا تعرف عني", "ماذا تتذكر عني", "ما الذي تتذكره عني",
        "فاكر عني ايه", "فاكر ايه عني", "انت فاكر عني ايه",
    ))
    if asks_facts:
        if not facts:
            answer = _style_text(
                "لا توجد حقائق محفوظة عنك حتى الآن.",
                "لسه مفيش معلومات محفوظة عنك.",
                style,
            )
        else:
            items = [f"{item['fact_key']}: {item['fact_value']}" for item in facts]
            answer = _style_text("أتذكر المعلومات التالية: ", "فاكر المعلومات دي: ", style) + "؛ ".join(items)
        return BrainReply(answer, "memory_facts", style)

    asks_history = _contains_any(normalized, (
        "ماذا قلت سابقا", "ماذا قلت سابقاً", "ما اخر ما قلته",
        "فاكر اخر حاجه قلتها", "اخر حاجه قلتها كانت ايه",
        "ماذا تحدثنا عنه", "كنا بنتكلم عن ايه",
    ))
    if asks_history:
        previous_user_messages = [
            item["content"] for item in history
            if item.get("role") == "user"
        ][-5:]
        if not previous_user_messages:
            answer = _style_text("لا يوجد سجل سابق في هذه الجلسة.", "مفيش كلام سابق في الجلسة دي.", style)
        else:
            answer = _style_text("آخر رسائلك كانت: ", "آخر رسايلك كانت: ", style) + "؛ ".join(previous_user_messages)
        return BrainReply(answer, "memory_history", style)
    return None


def _rule_reply(text: str, style: str) -> Optional[BrainReply]:
    q = _normalize(text)
    if not q:
        return BrainReply("اكتب رسالتك أولًا.", "empty", style)

    greetings = ("مرحبا", "السلام عليكم", "صباح الخير", "مساء الخير", "اهلا", "هاي", "hello", "hi")
    if _contains_any(q, greetings):
        return BrainReply(_style_text("أهلًا بك! كيف أستطيع مساعدتك؟", "أهلاً بيك! أقدر أساعدك في إيه؟", style), "greeting", style)

    if _contains_any(q, ("ازيك", "كيف حالك", "عامل ايه", "عامله ايه")):
        return BrainReply(_style_text("أنا بخير، شكرًا لسؤالك. كيف حالك؟", "تمام، شكرًا لسؤالك! إنت عامل إيه؟", style), "wellbeing", style)

    if _contains_any(q, ("شكرا", "متشكر", "تسلم", "thank you", "thanks")):
        return BrainReply(_style_text("على الرحب والسعة!", "العفو، تحت أمرك!", style), "thanks", style)

    if _contains_any(q, ("من انت", "انت مين", "ما هو jon2", "ما هو جون2")):
        answer = _style_text(
            "أنا Jon2 Lite، نواة تجريبية خفيفة. أستخدم قواعد محدودة، ولم يتم توصيل نموذج لغوي مدرّب بي بعد.",
            "أنا Jon2 Lite، نسخة تجريبية خفيفة. بفهم حاليًا طلبات محدودة بقواعد بسيطة، ولسه مفيش نموذج لغوي متوصل بيا.",
            style,
        )
        return BrainReply(answer, "identity", style)

    if _contains_any(q, ("ماذا تستطيع", "كيف يمكنك مساعدتي", "ما الذي يمكنك فعله", "بتقدر تعمل ايه", "تقدر تساعدني في ايه", "بتعمل ايه")):
        answer = _style_text(
            "أستطيع الرد على التحيات والشكر والتعريف بنفسي واسترجاع معلومات محفوظة في الجلسة.",
            "أقدر أرد على التحيات والشكر وأعرّفك بنفسي وأرجع معلومات محفوظة في الجلسة.",
            style,
        )
        return BrainReply(answer, "capabilities", style)

    if _contains_any(q, ("هل انت ذكاء اصطناعي", "هل انت نموذج", "انت حقيقي", "انت انسان")):
        answer = _style_text(
            "أنا برنامج تجريبي لمعالجة اللغة، لكنني لست نموذجًا لغويًا مدرّبًا حتى الآن.",
            "أنا برنامج تجريبي للتعامل مع الكلام، لكن لسه مش نموذج ذكاء اصطناعي مدرّب.",
            style,
        )
        return BrainReply(answer, "model_status", style)

    if _contains_any(q, ("ما معنى", "ماذا يعني", "اشرح لي", "اشرحلي", "يعني ايه", "معني")):
        answer = _style_text(
            "أحتاج إلى تحديد المصطلح أو إتاحة نموذج لغوي حتى أشرح هذا السؤال بدقة.",
            "حددلي الكلمة أو المصطلح المقصود، لأن الشرح العام لسه محتاج نموذج لغوي.",
            style,
        )
        return BrainReply(answer, "explanation_request", style)

    if q.endswith("?") or q.endswith("؟") or _contains_any(q, ("لماذا", "كيف", "متى", "اين", "كم", "هل", "ليه", "ازاي", "امتي", "فين")):
        answer = _style_text(
            "هذا سؤال يحتاج إلى فهم أوسع أو معلومات موثوقة. لا أملك نموذجًا لغويًا متصلًا الآن، لذلك لن أخمّن الإجابة.",
            "السؤال ده محتاج فهم أو معلومات أكتر. مفيش نموذج لغوي متوصل بيا دلوقتي، فعشان كده مش هخمن الإجابة.",
            style,
        )
        return BrainReply(answer, "unsupported_question", style)
    return None


def generate_with_model(prompt: str, language_style: str, adapter: Optional[ModelAdapter] = None) -> str:
    """Call only an explicitly injected local adapter; never a remote provider."""
    if adapter is None:
        raise RuntimeError("local_model_not_configured")
    return adapter(prompt, language_style)


def respond(
    text: str,
    model_adapter: Optional[ModelAdapter] = None,
    history: Sequence[dict] = (),
    facts: Sequence[dict] = (),
) -> BrainReply:
    style = detect_style(text)
    memory_result = _memory_reply(_normalize(text), style, history, facts)
    if memory_result is not None:
        return memory_result
    rule_result = _rule_reply(text, style)
    if rule_result is not None:
        return rule_result
    reasoning_result = reason(text, style, history=history, facts=facts)
    if reasoning_result is not None:
        return BrainReply(reasoning_result.answer, reasoning_result.intent, style)
    if model_adapter is not None:
        return BrainReply(generate_with_model(text, style, model_adapter), "model", style, True)
    fallback = _style_text(
        "لم أفهم الطلب بدقة بعد. هذه النسخة لا تحتوي على نموذج لغوي متصل؛ جرّب سؤالًا أو طلبًا أوضح.",
        "لسه مش قادر أفهم الطلب ده بدقة. النسخة دي مفيهاش نموذج لغوي متوصل؛ جرّب توضح طلبك.",
        style,
    )
    return BrainReply(fallback, "unsupported", style)
