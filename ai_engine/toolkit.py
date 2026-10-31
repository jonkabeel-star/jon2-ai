"""Project-owned tool catalog and prompt policies for Jon2 AI.

These are software tools around the base language model. They do not pretend to
be separate trained models; each tool routes a task through the same loaded model.
"""
from __future__ import annotations

from typing import Final

TOOL_PROMPTS: Final[dict[str, str]] = {
    "chat": (
        "أجب عن سؤال المستخدم مباشرة. إذا كانت المعلومة غير مؤكدة فاذكر ذلك، "
        "ولا تختلق حقائق أو مصادر."
    ),
    "story": (
        "أنت كاتب قصص محترف. اكتب قصة مترابطة ذات بداية ووسط ونهاية، "
        "وحافظ على ثبات أسماء الشخصيات وصفاتها وتسلسل الأحداث. تجنب التكرار "
        "والقفزات غير المبررة. إذا طلب المستخدم قصة للأطفال فاجعلها مناسبة للعائلة."
    ),
    "summarize": (
        "لخّص النص الذي يقدمه المستخدم دون إضافة معلومات من عندك. احتفظ بالأفكار "
        "الرئيسية والأرقام والأسماء المهمة. استخدم نقاطًا واضحة، واجعل الملخص "
        "أقصر من النص الأصلي."
    ),
    "rewrite": (
        "أعد صياغة النص مع الحفاظ على المعنى والمعلومات. حسّن الوضوح والترابط "
        "واللغة، ولا تضف ادعاءات جديدة. إذا لم يحدد المستخدم أسلوبًا فاختر أسلوبًا "
        "طبيعيًا وواضحًا."
    ),
    "translate": (
        "ترجم النص بأمانة إلى اللغة التي يحددها المستخدم. إذا لم يحدد لغة الهدف، "
        "اسأله عن اللغة المطلوبة بدل التخمين. حافظ على الأسماء والأرقام والمعنى."
    ),
    "ideas": (
        "اقترح أفكارًا عملية ومختلفة مرتبطة بطلب المستخدم. اشرح كل فكرة بإيجاز، "
        "ولا تدّعِ أن فكرة ما مضمونة النجاح."
    ),
    "code": (
        "ساعد في البرمجة بكود واضح قابل للتشغيل. اذكر الافتراضات والمتطلبات، "
        "وتجنب الادعاء بأنك شغّلت الكود أو اختبرته ما لم يحدث ذلك فعليًا."
    ),
}

TOOL_LABELS: Final[dict[str, str]] = {
    "chat": "المحادثة العامة",
    "story": "كاتب القصص",
    "summarize": "تلخيص النصوص",
    "rewrite": "إعادة الصياغة",
    "translate": "الترجمة",
    "ideas": "توليد الأفكار",
    "code": "مساعد البرمجة",
}


def get_tool_prompt(tool: str) -> str:
    """Return a validated task policy; unknown tools fail closed."""
    try:
        return TOOL_PROMPTS[tool]
    except KeyError as exc:
        raise ValueError("الأداة المطلوبة غير متاحة.") from exc


def available_tools() -> list[dict[str, str]]:
    """Return public metadata for the allowlisted tools."""
    return [
        {"id": tool_id, "name": TOOL_LABELS[tool_id]}
        for tool_id in TOOL_PROMPTS
    ]
