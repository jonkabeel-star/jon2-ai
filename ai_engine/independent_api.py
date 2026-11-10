"""Independent Jon2 API: original local checkpoint + SQLite memory only.

This service deliberately has no Cloudflare Workers AI, hosted LLM, web-search,
or third-party model fallback. It is a separate runtime and does not replace the
existing production Worker or public website until reviewed and deployed.
"""
from __future__ import annotations

import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

import chat_memory
from chat_engine import (
    CHECKPOINT_PATH,
    generate_reply,
    load_runtime,
    model_is_ready,
)

APP_VERSION = "0.1.0"
_RELEASE_FLAG = "JON2_INDEPENDENT_CHAT_RELEASE_APPROVED"

app = FastAPI(
    title="Jon2 Independent Core",
    description=(
        "Standalone Jon2 runtime using only project-owned model weights "
        "and local SQLite conversation memory."
    ),
    version=APP_VERSION,
)

_origins = [
    item.strip()
    for item in os.getenv(
        "JON2_INDEPENDENT_ALLOWED_ORIGINS",
        "https://jon2-ai.pages.dev,https://jonkabeel-star.github.io",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
    )


def _release_approved() -> bool:
    return os.getenv(_RELEASE_FLAG, "false").strip().lower() == "true"


def _checkpoint_exists() -> bool:
    return CHECKPOINT_PATH.is_file()


@app.get("/")
def home():
    return {
        "project": "Jon2 Independent Core",
        "status": "online",
        "version": APP_VERSION,
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    checkpoint_exists = _checkpoint_exists()
    approved = _release_approved()
    loaded = model_is_ready()
    return {
        "project": "Jon2 Independent Core",
        "version": APP_VERSION,
        "status": "online",
        "runtime": "project_owned_jon2_checkpoint",
        "external_ai_provider": False,
        "external_knowledge_fallback": False,
        "memory": "local_sqlite",
        "checkpoint_present": checkpoint_exists,
        "model_loaded": loaded,
        "release_approved": approved,
        "chat_ready": bool(checkpoint_exists and loaded and approved),
    }


@app.get("/api/health/ready")
def readiness():
    if _release_approved() and _checkpoint_exists() and not model_is_ready():
        try:
            load_runtime()
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail="تعذر تحميل نموذج Jon2 الأصلي على هذا الخادم.",
            ) from error
    snapshot = health()
    if not snapshot["chat_ready"]:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": (
                    "checkpoint_missing" if not snapshot["checkpoint_present"]
                    else "human_release_approval_required"
                    if not snapshot["release_approved"]
                    else "model_not_loaded"
                ),
            },
        )
    return {"project": "Jon2 Independent Core", "status": "ready"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    if not _release_approved():
        raise HTTPException(
            status_code=503,
            detail="نموذج Jon2 الأصلي ما زال تحت التطوير ولم يحصل على موافقة الإطلاق.",
        )
    if not _checkpoint_exists():
        raise HTTPException(
            status_code=503,
            detail="ملف أوزان Jon2 الأصلي غير متاح على هذا الخادم.",
        )

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="اكتب رسالتك أولًا.")

    try:
        history = chat_memory.recent_messages(request.session_id, limit=8)
        memories = chat_memory.relevant_memories(
            request.session_id, message, limit=4
        )
        reply = generate_reply(message, history, memories)
        chat_memory.add_exchange(request.session_id, message, reply)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "project": "Jon2 Independent Core",
        "reply": reply,
        "session_id": request.session_id,
        "memory_used": bool(memories),
        "response_mode": "original_jon2_model",
    }


@app.get("/api/memory/{session_id}")
def memory_status(session_id: str):
    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        session_id,
    ):
        raise HTTPException(status_code=422, detail="معرّف الجلسة غير صالح.")
    return {
        "project": "Jon2 Independent Core",
        **chat_memory.session_stats(session_id),
    }
