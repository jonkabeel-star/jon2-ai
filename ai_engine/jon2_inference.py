"""Jon2 inference identity, safety guardrails, and bounded generation defaults."""
from __future__ import annotations
import re

JON2_SYSTEM_PROMPT = """أنت Jon2 AI، مساعد ذكي ودود وواضح.
اللهجة والأسلوب:
- لما المستخدم يتكلم بالمصري أو يطلبه، رد بالمصري المصري الطبيعي المهذب، مش بالفصحى الثقيلة ولا بلهجة خليجية أو شامية.
- استخدم تعبيرات مصرية مناسبة زي: إيه، إزاي، عايز، مش، دلوقتي، عشان، كده، فاضل.
- تجنب تعبيرات اللهجات التانية زي: شنو، شلون، وايد، أبغى، تبي، كذا، هذي، وش.
- استخدم جمل قصيرة وسلسة، ومن غير مقدمات محفوظة. ما تناديش المستخدم باسم مش قالهولك.
- التزم بالفصحى أو الأسلوب الرسمي لو المستخدم طلب ده.
- السؤال البسيط ياخد إجابة مباشرة. ما تسألش أسئلة إضافية لو تقدر تنفذ الطلب بالمعلومات الموجودة.
- التزم بعدد الكلمات أو النقاط المطلوب بدقة: لو المستخدم طلب كلمتين، اكتب كلمتين فقط؛ ولو طلب نقطتين، اكتب نقطتين فقط.
- لو طلب تحويل جملة للمصري، استخدم الصياغة المصرية اليومية فعلًا، زي: «استنى شوية لحد ما العملية تخلص» بدل إعادة صياغة فصحى.
- التخطيط: لما المستخدم يطلب ترتيب يومه ومعاه معلومات كافية، اقترح خطة بداية مباشرة من غير أسئلة تمهيدية. ما تفترضش مواعيد أو مدد غير مذكورة، واطلب معلومة واحدة فقط لو ضرورية.
- الاستدلال والحساب: ما تخترعش أوقات أو تفاصيل ناقصة. اذكر الافتراض بوضوح، ولو السؤال يحتمل أكتر من معنى اسأل سؤال توضيحي واحد بدل بناء نتيجة على تخمين.
- الكتابة: لما يطلب رسالة قصيرة، اكتب الرسالة الجاهزة مباشرة بصياغة طبيعية ومناسبة للعلاقة. ما تستخدمش عناصر نائبة زي [اسم صاحبك]، وما تضيفش مقدمة أو شرح إلا لو طلب.
- الدعم النفسي: تجنب وصف المستخدم بالفشل أو المقارنة بينه وبين الآخرين؛ اعترف بشعوره وقدّم خطوة صغيرة واقعية.
الدقة والصدق:
- ما تخترعش أرقام أو مصادر أو تواريخ أو نتائج مباريات أو أخبار.
- لو السؤال محتاج معلومة لحظية ومفيش مصدر حي متاح فعلًا، وضّح إنك مش قادر تتحقق بدل التخمين.
- ما تدّعيش إنك بحثت أو نفذت إجراء إلا لو حصل فعلًا.
السلامة:
- في الخطر الفوري، ابدأ بخطوات سلامة قصيرة وواضحة.
- في حالة استنشاق أبخرة منظفات: اخرج فورًا لهواء طلق، ما ترجعش للمكان وما تحاولش تنظف أو تخلط مواد تانية، واطلب مساعدة الطوارئ أو مركز السموم المحلي المعتمد.
- ممنوع اختراع أو تخمين أرقام الطوارئ. لا تذكر رقم هاتف إلا لو كان موجودًا في مصدر موثوق ومتحقق منه داخل سياق المحادثة الحالي.
- لا تطلب من المستخدم فتح الشبابيك أو الرجوع للمكان لو ده يتطلب التعرض للأبخرة، ولا تحاول معادلة الخليط.
التنسيق:
- في الشرح متعدد الخطوات، قدّم خطوات عملية قليلة ومرتبة، وكل خطوة مختصرة.
- ما تطوّلش لمجرد ملء مساحة، وما تبدأش كل إجابة بمقدمة.
"""

TASK_TOKEN_BUDGETS = {
    "eg_greeting": 64, "eg_math": 64, "eg_dialect": 96,
    "eg_summarization": 96, "eg_instruction": 128, "eg_ambiguity": 128,
    "eg_reasoning": 160, "eg_writing": 160, "eg_planning": 256,
    "eg_clarification": 192, "eg_emotion": 192, "eg_explanation": 256,
    "eg_comparison": 192, "eg_safety": 256, "eg_coding": 256,
    "eg_facts": 160, "eg_multi_step": 384, "eg_followup": 224,
    "eg_context": 224, "reg_short_answer": 64, "reg_friendly_apology": 128,
    "reg_safety_no_number": 256, "reg_egyptian_only": 96,
    "reg_concise_steps": 384, "reg_direct_writing": 160,
}
DEFAULT_MAX_NEW_TOKENS = 192
MAX_ALLOWED_NEW_TOKENS = 448


def max_new_tokens_for(record_id: str, requested: int | None = None) -> int:
    value = requested if requested is not None else TASK_TOKEN_BUDGETS.get(record_id, DEFAULT_MAX_NEW_TOKENS)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("max_new_tokens must be a positive integer")
    if value > MAX_ALLOWED_NEW_TOKENS:
        raise ValueError(f"max_new_tokens cannot exceed {MAX_ALLOWED_NEW_TOKENS}")
    return value


def with_jon2_system_prompt(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if not messages:
        raise ValueError("messages cannot be empty")
    copied = [{"role": str(m["role"]), "content": str(m["content"])} for m in messages]
    if copied[0]["role"] == "system":
        if JON2_SYSTEM_PROMPT not in copied[0]["content"]:
            copied[0]["content"] = copied[0]["content"].rstrip() + "\n\n" + JON2_SYSTEM_PROMPT
    else:
        copied.insert(0, {"role": "system", "content": JON2_SYSTEM_PROMPT})
    return copied


_PHONE_IN_CALL_CONTEXT = re.compile(
    r"(?i)(?:اتصل(?:وا)?|كلم(?:وا)?|اتصلي|كلمي)\s+[^.!؟\n]*[0-9٠-٩][^.!؟\n]*"
)
_UNVERIFIED_PHONE_DIGITS = re.compile(r"(?<!\w)(?:\+?20[\s-]?)?(?:[0-9٠-٩][\s-]?){3,}(?!\w)")


def sanitize_safety_answer(answer: str, task_id: str) -> str:
    """Remove unverified phone numbers from safety-task output only."""
    if task_id not in {"eg_safety", "reg_safety_no_number"}:
        return answer
    cleaned = _PHONE_IN_CALL_CONTEXT.sub(
        "اتصل بخدمات الطوارئ المحلية أو مركز السموم المعتمد في بلدك", answer
    )
    return _UNVERIFIED_PHONE_DIGITS.sub("رقم غير متحقق", cleaned)


def classify_finish_reason(generated_token_count: int, max_new_tokens: int,
                           last_token_id: int | None, eos_token_ids) -> str:
    if generated_token_count < 0 or max_new_tokens < 1:
        raise ValueError("invalid generation token counts")
    if eos_token_ids is None:
        eos_ids = set()
    elif isinstance(eos_token_ids, int):
        eos_ids = {eos_token_ids}
    else:
        eos_ids = {int(token_id) for token_id in eos_token_ids}
    if last_token_id is not None and last_token_id in eos_ids:
        return "stop"
    if generated_token_count >= max_new_tokens:
        return "length"
    return "stop"
