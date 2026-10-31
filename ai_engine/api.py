"""HTTP API for the Jon2 AI hybrid Python runtime.

Run from the repository root:
    uvicorn api:app --app-dir ai_engine --host 0.0.0.0 --port 8000

The model loads on the first chat request, not during health checks.
This starter API is for controlled testing; add authentication, persistent
storage, and shared rate limiting before exposing it as a public service.
"""
from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hybrid_engine import engine


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)


app = FastAPI(
    title="Jon2 AI Python Engine",
    version="0.1.0",
    description="Arabic-first hybrid AI runtime for Jon2 AI.",
    docs_url="/api/docs",
    redoc_url=None,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "JON2_ALLOWED_ORIGINS",
        "https://jonkabeel-star.github.io,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "project": "Jon2 AI",
        "service": "python-hybrid-engine",
        "status": "online",
        "model_loaded": engine.ready,
        "model_repo": os.getenv(
            "JON2_MODEL_REPO",
            "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        ),
        "model_quantization": os.getenv("JON2_MODEL_FILE", "*q4_k_m.gguf"),
        "public_launch_ready": False,
    }


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
    try:
        reply = engine.reply(
            payload.message,
            [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in payload.history],
        )
        return {"reply": reply, "model": "Jon2 Hybrid"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
