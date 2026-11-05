"""Locked-by-default, temporary Jais 2 ZeroGPU proof of concept.

No model is downloaded or loaded unless the owner explicitly sets all
rights/access gates and supplies a gated Hugging Face token as a Space secret.
"""
from __future__ import annotations

import os
import re

import gradio as gr
import spaces

MODEL_ID = "inception42/Jais-2-8B-Chat"
SYSTEM_PROMPT = (
    "أنت Jon2 Arabic. أجب باللهجة المصرية الطبيعية عندما يناسب السياق، "
    "وافهم العربية الفصحى وأجب بها عند طلبها. لا تخترع معلومات، "
    "وإذا لم تعرف فقل ذلك بوضوح."
)

RIGHTS_APPROVED = os.getenv("JON2_MODEL_RIGHTS_APPROVED", "").strip() == "YES"
HF_TERMS_ACCEPTED = os.getenv("JON2_HF_ACCESS_ACCEPTED", "").strip() == "YES"
REVISION = os.getenv("JON2_MODEL_REVISION", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
REVISION_VALID = bool(re.fullmatch(r"[0-9a-fA-F]{40}", REVISION))
MODEL_ENABLED = RIGHTS_APPROVED and HF_TERMS_ACCEPTED and REVISION_VALID and bool(HF_TOKEN)

tokenizer = None
model = None
load_error = None

if MODEL_ENABLED:
    # Import spaces before torch; ZeroGPU requires model initialization at
    # module scope so it can prepare/stream the weights to its allocated GPU.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            revision=REVISION,
            token=HF_TOKEN,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            revision=REVISION,
            token=HF_TOKEN,
            torch_dtype="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=False,
        ).to("cuda")
        model.eval()
    except Exception as exc:  # Keep secrets and prompts out of logs/UI.
        load_error = type(exc).__name__
        tokenizer = None
        model = None


def status_text() -> str:
    if not RIGHTS_APPROVED:
        return "موقوف: لم يتم اعتماد حقوق بيانات التدريب بعد."
    if not HF_TERMS_ACCEPTED:
        return "موقوف: لم يؤكد مالك المشروع قبول شروط الوصول بنفسه."
    if not REVISION_VALID:
        return "موقوف: يلزم تثبيت نسخة نموذج محددة ببصمة SHA من 40 خانة."
    if not HF_TOKEN:
        return "موقوف: أضف HF_TOKEN كسرّ خاص في إعدادات Space، ولا تضعه في الكود."
    if load_error:
        return f"تعذر تحميل النموذج ({load_error}). لم يتم تفعيل المحادثة."
    if model is None or tokenizer is None:
        return "النموذج غير جاهز."
    return "النموذج محمّل داخل جلسة GPU مؤقتة."


def _validate_message(message: str) -> str:
    if not isinstance(message, str) or not message.strip():
        raise gr.Error("اكتب رسالة أولًا.")
    message = message.strip()
    if len(message) > 1500:
        raise gr.Error("الحد الأقصى للرسالة 1500 حرف.")
    return message


def reply_locked(message: str) -> str:
    # Keep locked requests off the GPU so they cannot consume ZeroGPU quota.
    raise gr.Error(status_text())


if MODEL_ENABLED:
    @spaces.GPU(duration=45)
    def reply_enabled(message: str) -> str:
        message = _validate_message(message)
        if model is None or tokenizer is None:
            raise gr.Error(status_text())

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs.pop("token_type_ids", None)
        input_device = model.get_input_embeddings().weight.device
        inputs = {key: value.to(input_device) for key, value in inputs.items()}

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=160,
                do_sample=False,
                repetition_penalty=1.08,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
        generated = output[0, inputs["input_ids"].shape[-1]:]
        answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
        if not answer:
            raise gr.Error("النموذج أعاد ردًا فارغًا.")
        return answer


handler = reply_enabled if MODEL_ENABLED else reply_locked


with gr.Blocks(title="Jon2 Arabic — ZeroGPU Test") as demo:
    gr.Markdown("# Jon2 Arabic — اختبار GPU مؤقت")
    status = status_text()
    gr.Markdown(f"**الحالة:** {status}")
    if not MODEL_ENABLED:
        gr.Markdown(
            "هذه النسخة مقفولة افتراضيًا. لن يتم تنزيل الأوزان أو تحميلها "
            "أو إرسال أي رسالة إلى خدمة استدلال خارجية قبل استيفاء الموافقات."
        )
    message = gr.Textbox(
        label="رسالتك",
        placeholder="اكتب سؤالًا بالعربية...",
        lines=3,
        max_lines=5,
        max_length=1500,
    )
    send = gr.Button("إرسال")
    answer = gr.Textbox(label="رد Jon2 Arabic", lines=6, interactive=False)
    send.click(fn=handler, inputs=message, outputs=answer)
    message.submit(fn=handler, inputs=message, outputs=answer)

if __name__ == "__main__":
    demo.launch()
