"""Private FastAPI inference service for a trained Jon2 Qwen3.5 LoRA adapter.

This service refuses chat requests until a GPU, base model, adapter, and
bearer token are configured. It is not deployed by adding this file.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_MODEL = os.getenv("JON2_BASE_MODEL", "Qwen/Qwen3.5-9B")
ADAPTER_DIR = Path(os.getenv("JON2_ADAPTER_PATH", "/models/jon2-qwen35-9b-lora"))
API_TOKEN = os.getenv("JON2_API_TOKEN", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("JON2_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

_state: dict = {"model": None, "tokenizer": None, "ready": False, "error": None}


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=24)
    max_new_tokens: int = Field(default=256, ge=16, le=512)
    temperature: float = Field(default=0.7, ge=0.1, le=1.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_TOKEN:
        _state["error"] = "JON2_API_TOKEN is not configured."
    elif not torch.cuda.is_available():
        _state["error"] = "CUDA GPU is unavailable."
    elif not (ADAPTER_DIR / "adapter_config.json").is_file():
        _state["error"] = f"LoRA adapter not found at {ADAPTER_DIR}."
    else:
        try:
            from transformers import AutoTokenizer, Qwen3_5ForCausalLM, BitsAndBytesConfig
            from peft import PeftModel

            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=False)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            quant = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.float16,
            )
            base = Qwen3_5ForCausalLM.from_pretrained(
                BASE_MODEL,
                quantization_config=quant,
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                trust_remote_code=False,
                attn_implementation="sdpa",
            )
            model = PeftModel.from_pretrained(base, str(ADAPTER_DIR), is_trainable=False)
            model.eval()
            _state.update(model=model, tokenizer=tokenizer, ready=True, error=None)
        except Exception as exc:
            _state["error"] = f"Model startup failed: {type(exc).__name__}: {exc}"
    yield
    _state.update(model=None, tokenizer=None, ready=False)


app = FastAPI(title="Jon2 AI Private Inference API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def require_token(authorization: str | None) -> None:
    if not API_TOKEN:
        raise HTTPException(status_code=503, detail="API token is not configured.")
    expected = f"Bearer {API_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized.")


@app.get("/api/health")
def health():
    return {
        "service": "Jon2 AI",
        "ready": bool(_state["ready"]),
        "base_model": BASE_MODEL,
        "adapter_present": (ADAPTER_DIR / "adapter_config.json").is_file(),
        "cuda_available": torch.cuda.is_available(),
        "error": _state["error"],
    }


@app.post("/api/chat")
@torch.inference_mode()
def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    require_token(authorization)
    if not _state["ready"]:
        raise HTTPException(status_code=503, detail="Jon2 model is not ready.")
    if payload.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The final message must be from the user.")
    messages = [message.model_dump() for message in payload.messages]
    tokenizer = _state["tokenizer"]
    model = _state["model"]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    output = model.generate(
        **inputs,
        max_new_tokens=payload.max_new_tokens,
        do_sample=payload.temperature > 0.1,
        temperature=payload.temperature,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    answer = tokenizer.decode(
        output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True,
    ).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="Model returned an empty response.")
    return {"reply": answer, "model": "Jon2 AI", "base_model": BASE_MODEL}
