"""Local-only inference adapter for the Jais 2 8B chat checkpoint.

This module never downloads weights and never calls a hosted inference API.
The caller must provide an already-approved, locally stored model directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MODEL_ID = "inception42/Jais-2-8B-Chat"
SYSTEM_PROMPT = (
    "أنت Jon2 Arabic، مساعد عربي مفيد ودقيق. "
    "تحدث باللهجة المصرية الطبيعية عندما يناسب السياق، "
    "وافهم العربية الفصحى وأجب بها عند طلبها. "
    "لا تخترع معلومات؛ إذا لم تعرف فقل ذلك بوضوح. "
    "كن واضحًا ومباشرًا، ولا تدّعِ أنك نفذت إجراءً لم تنفذه."
)

_tokenizer: Any | None = None
_model: Any | None = None
_model_path: Path | None = None


def _configured_path() -> Path:
    raw = os.getenv("JON2_JAIS2_LOCAL_PATH", "").strip()
    if not raw:
        raise RuntimeError(
            "JON2_JAIS2_LOCAL_PATH is not configured. "
            "A rights-approved local checkpoint is required."
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Local Jais 2 model directory not found: {path}")
    return path


def model_is_ready() -> bool:
    return _model is not None and _tokenizer is not None


def load_runtime() -> None:
    """Load only from local disk; network access is explicitly disabled."""
    global _tokenizer, _model, _model_path
    if model_is_ready():
        return

    path = _configured_path()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _tokenizer = AutoTokenizer.from_pretrained(
        str(path),
        local_files_only=True,
        trust_remote_code=False,
    )
    _model = AutoModelForCausalLM.from_pretrained(
        str(path),
        local_files_only=True,
        trust_remote_code=False,
        device_map="auto",
        torch_dtype="auto",
        low_cpu_mem_usage=True,
    )
    _model.eval()
    _model_path = path


def generate_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    max_new_tokens: int = 384,
) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("اكتب رسالتك أولًا.")
    if max_new_tokens < 1 or max_new_tokens > 1024:
        raise ValueError("max_new_tokens must be between 1 and 1024.")

    load_runtime()

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    for item in (history or [])[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:2000]})
    messages.append({"role": "user", "content": message.strip()[:2000]})

    import torch

    prompt = _tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = _tokenizer(prompt, return_tensors="pt")
    input_device = _model.get_input_embeddings().weight.device
    inputs = {key: value.to(input_device) for key, value in inputs.items()}

    with torch.inference_mode():
        output = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.08,
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.pad_token_id or _tokenizer.eos_token_id,
        )

    generated = output[0, inputs["input_ids"].shape[-1]:]
    answer = _tokenizer.decode(generated, skip_special_tokens=True).strip()
    if not answer:
        raise RuntimeError("Jais 2 returned an empty response.")
    return answer
