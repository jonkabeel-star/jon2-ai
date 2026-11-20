"""Private Qwen3.5-4B inference runtime for Jon2.

The runtime uses the official instruction-tuned Qwen3.5-4B checkpoint as a
third-party base model. A Jon2 LoRA adapter is optional until it is trained
from separately approved data. Public chat remains blocked by independent
inference, quality-review, and owner-release gates.
"""
from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ai_engine.conversation_context import (
    ConversationContextError,
    build_context_messages,
)

BASE_MODEL = os.getenv("JON2_BASE_MODEL", "Qwen/Qwen3.5-4B")
ADAPTER_PATH = os.getenv("JON2_ADAPTER_PATH", "").strip()
ADAPTER_DIR = Path(ADAPTER_PATH).expanduser() if ADAPTER_PATH else None
RUNTIME_TOKEN = os.getenv("JON2_RUNTIME_TOKEN", "")
PUBLIC_CHAT_ENABLED = os.getenv("JON2_PUBLIC_CHAT_ENABLED", "false").lower() == "true"
INFERENCE_TESTED = os.getenv("JON2_INFERENCE_TESTED", "false").lower() == "true"
QUALITY_REVIEW_PASSED = os.getenv("JON2_QUALITY_REVIEW_PASSED", "false").lower() == "true"
MAX_INPUT_TOKENS = int(os.getenv("JON2_MAX_INPUT_TOKENS", "6144"))
MAX_HISTORY_MESSAGES = 40
MAX_NEW_TOKENS = 256

SYSTEM_PROMPT = (
    "أنت مساعد Jon2 AI. أجب بالعربية الواضحة، واستخدم اللهجة المصرية الطبيعية "
    "إذا كتب المستخدم بالمصري. كن دقيقًا ومباشرًا. لا تخترع حقائق أو أرقامًا "
    "أو مصادر. إذا لم تعرف، قل ذلك بوضوح. لا تدّعِ أنك نموذج مدرّب خصيصًا باسم Jon2."
)

_state: dict = {
    "model": None, "tokenizer": None, "ready": False,
    "adapter_loaded": False, "error": None,
}


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class RuntimeChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)
    session_id: str | None = Field(default=None, max_length=64)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(RUNTIME_TOKEN) < 32:
        _state["error"] = "JON2_RUNTIME_TOKEN must contain at least 32 characters."
    elif not torch.cuda.is_available():
        _state["error"] = "CUDA GPU is unavailable; CPU inference is disabled."
    else:
        try:
            from transformers import (
                AutoTokenizer,
                BitsAndBytesConfig,
                Qwen3_5ForCausalLM,
            )

            tokenizer = AutoTokenizer.from_pretrained(
                BASE_MODEL, trust_remote_code=False
            )
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
            model = Qwen3_5ForCausalLM.from_pretrained(
                BASE_MODEL,
                quantization_config=quantization,
                device_map={"": 0},
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                trust_remote_code=False,
                attn_implementation="sdpa",
            )

            adapter_loaded = False
            if ADAPTER_DIR is not None and (ADAPTER_DIR / "adapter_config.json").is_file():
                from peft import PeftModel
                model = PeftModel.from_pretrained(
                    model, str(ADAPTER_DIR), is_trainable=False
                )
                adapter_loaded = True

            model.eval()
            _state.update(
                model=model,
                tokenizer=tokenizer,
                ready=True,
                adapter_loaded=adapter_loaded,
                error=None,
            )
        except Exception as exc:
            _state["error"] = f"{type(exc).__name__}: {exc}"
    yield
    _state.update(model=None, tokenizer=None, ready=False, adapter_loaded=False)


app = FastAPI(
    title="Jon2 Qwen3.5-4B Private Runtime",
    version="1.1.0",
    lifespan=lifespan,
)


def _authorized(authorization: str | None) -> bool:
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    return len(RUNTIME_TOKEN) >= 32 and bool(supplied) and hmac.compare_digest(
        RUNTIME_TOKEN, supplied
    )


def _template_token_count(tokenizer, messages: list[dict[str, str]]) -> int:
    encoded = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True
    )
    if isinstance(encoded, dict):
        token_ids = encoded["input_ids"]
    else:
        token_ids = encoded
    if hasattr(token_ids, "shape"):
        return int(token_ids.shape[-1])
    if token_ids and isinstance(token_ids[0], (list, tuple)):
        return len(token_ids[0])
    return len(token_ids)


@app.get("/v1/health")
def health():
    return {
        "contract_version": "1",
        "project": "Jon2 AI",
        "api_ready": len(RUNTIME_TOKEN) >= 32,
        "model_ready": bool(_state["ready"]),
        "model_status": "ready" if _state["ready"] else (
            "error" if _state["error"] else "loading"
        ),
        "base_model": BASE_MODEL,
        "adapter_loaded": bool(_state["adapter_loaded"]),
        "inference_tested": INFERENCE_TESTED,
        "quality_review_passed": QUALITY_REVIEW_PASSED,
        "public_chat_enabled": PUBLIC_CHAT_ENABLED,
        "context_manager": "turn_aware_token_budget_v1",
        "max_history_messages": MAX_HISTORY_MESSAGES,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "error": _state["error"],
    }


@app.post("/v1/chat")
@torch.inference_mode()
def chat(
    payload: RuntimeChatRequest,
    authorization: str | None = Header(default=None),
):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Runtime authentication failed.")
    if not _state["ready"]:
        raise HTTPException(status_code=503, detail="Qwen3.5 runtime is not ready.")

    tokenizer = _state["tokenizer"]
    model = _state["model"]
    try:
        messages, context_meta = build_context_messages(
            system_prompt=SYSTEM_PROMPT,
            history=[item.model_dump() for item in payload.history],
            current_message=payload.message,
            count_tokens=lambda candidate: _template_token_count(tokenizer, candidate),
            max_input_tokens=MAX_INPUT_TOKENS,
            max_history_messages=MAX_HISTORY_MESSAGES,
        )
    except ConversationContextError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)
    generated = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=True,
        temperature=0.7,
        top_p=0.8,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    new_tokens = generated[:, inputs["input_ids"].shape[1]:]
    reply = tokenizer.decode(
        new_tokens[0], skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    ).strip()
    if not reply:
        raise HTTPException(status_code=502, detail="Model returned an empty response.")

    return {
        "contract_version": "1",
        "reply": reply,
        "model": BASE_MODEL,
        "adapter_loaded": bool(_state["adapter_loaded"]),
        "response_mode": "jon2_lora" if _state["adapter_loaded"] else "qwen35_base_preview",
        "context": context_meta,
    }
