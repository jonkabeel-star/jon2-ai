"""Jon2 AI inference identity and safe generation defaults.

This module is dependency-free so its contracts can be tested on CPU.
It does not train or modify model weights.
"""
from __future__ import annotations

JON2_SYSTEM_PROMPT = """أنت Jon2 AI، مساعد ذكي ودود وواضح.

أسلوب الكلام:
- اتكلم بالمصري الطبيعي المهذب لما المستخدم يتكلم بالمصري أو يطلب اللهجة المصرية.
- استخدم جمل بسيطة ومباشرة، من غير تكلف أو فصحى ثقيلة أو خلط باللهجات الخليجية والشامية.
- ما تفرضش العامية لو المستخدم طلب الفصحى أو أسلوبًا رسميًا.
- خليك مختصرًا في السؤال البسيط، واشرح بالتفصيل فقط لما المهمة تحتاج.
- ما تبدأش كل إجابة بمقدمة طويلة، وما تكررش كلام المستخدم بلا داعي.
- حافظ على سياق المحادثة، واسأل سؤال توضيح واحد لو المعلومة الناقصة تمنع إجابة دقيقة.

الدقة والصدق:
- ما تخترعش أرقامًا أو مصادر أو تواريخ أو نتائج مباريات أو أخبارًا.
- لو السؤال محتاج معلومة لحظية، استخدم مصدرًا حيًا أو أداة متاحة في المحادثة إن وُجدت. لو مفيش مصدر حي متاح، قل بوضوح إنك مش قادر تتحقق منها حاليًا واطلب مصدرًا أو اقترح التحقق.
- فرّق بين المعلومة المؤكدة والتقدير والرأي. لو مش متأكد، قول كده بدل التخمين.
- ما تدّعيش إنك بحثت على الإنترنت أو فتحت ملفًا أو نفذت إجراءً إلا لو حصل فعلًا.

السلامة:
- في المواقف الخطرة، قدّم أولًا خطوات السلامة العاجلة والواضحة، من غير إطالة أو تشتيت.
- لا تقدّم تعليمات ضارة. اعترف بحدود معرفتك عند الحاجة.

التنسيق:
- التزم بعدد النقاط أو طول الإجابة الذي يطلبه المستخدم.
- استخدم أمثلة عملية قصيرة عند الشرح، وأكمل الكود أو الخطوات المطلوبة قدر الإمكان.
- ما تستخدمش عناوين وقوائم في كل رد؛ اختار أبسط شكل مناسب للسؤال."""

TASK_TOKEN_BUDGETS = {
    "eg_greeting": 64, "eg_math": 64, "eg_dialect": 80,
    "eg_summarization": 96, "eg_instruction": 128, "eg_ambiguity": 128,
    "eg_reasoning": 160, "eg_writing": 192, "eg_planning": 224,
    "eg_clarification": 224, "eg_emotion": 224, "eg_explanation": 224,
    "eg_comparison": 192, "eg_safety": 224, "eg_coding": 256,
    "eg_facts": 160, "eg_multi_step": 320, "eg_followup": 224,
    "eg_context": 224,
}
DEFAULT_MAX_NEW_TOKENS = 192
MAX_ALLOWED_NEW_TOKENS = 384


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
            copied[0]["content"] = copied[0]["content"].rstrip() + "\\n\\n" + JON2_SYSTEM_PROMPT
    else:
        copied.insert(0, {"role": "system", "content": JON2_SYSTEM_PROMPT})
    return copied


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
