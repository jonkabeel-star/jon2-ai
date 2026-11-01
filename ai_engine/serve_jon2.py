"""Private inference API for a locally trained original Jon2 checkpoint.

No pretrained model or paid inference API is used. The service refuses chat
requests until a real trained checkpoint is configured.
"""
from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from jon2_core import generate, load_model

APP_DIR = Path(__file__).resolve().parent
CHECKPOINT = Path(os.environ.get(
    "JON2_CHECKPOINT",
    APP_DIR / "checkpoints" / "jon2-small.pt",
))
MAX_NEW_TOKENS = int(os.environ.get("JON2_MAX_NEW_TOKENS", "180"))
DEVICE = os.environ.get("JON2_DEVICE", "").strip() or None

app = FastAPI(title="Jon2 AI Original Inference", version="1.0.0")
_model = None
_tokenizer = None
_device = None
_lock = Lock()
_load_error = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def load_checkpoint():
    global _model, _tokenizer, _device, _load_error
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        if not CHECKPOINT.is_file():
            _load_error = f"Checkpoint not found: {CHECKPOINT}"
            return
        try:
            _model, _tokenizer, _device = load_model(str(CHECKPOINT), DEVICE)
            _load_error = None
        except Exception as exc:
            _load_error = f"Checkpoint could not be loaded: {type(exc).__name__}"
            _model = _tokenizer = _device = None


@app.on_event("startup")
def startup():
    load_checkpoint()


@app.get("/health")
def health():
    load_checkpoint()
    return {
        "service": "Jon2 AI Original Inference",
        "status": "ready" if _model is not None else "not_ready",
        "model": "Jon2 Original Transformer",
        "checkpoint_configured": CHECKPOINT.is_file(),
        "device": str(_device) if _device is not None else None,
        "detail": _load_error,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    load_checkpoint()
    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="نموذج Jon2 المدرّب غير متوفر حاليًا. لم يتم توليد إجابة وهمية.",
        )
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="اكتب رسالتك أولًا.")
    try:
        output = generate(
            _model,
            _tokenizer,
            message,
            _device,
            max_new_chars=MAX_NEW_TOKENS,
            temperature=0.75,
        )
        reply = output[len(message):].strip()
        if not reply:
            raise RuntimeError("Model generated an empty continuation.")
        return {"reply": reply, "model": "Jon2 Original Transformer"}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"تعذر توليد الرد: {type(exc).__name__}",
        ) from exc
