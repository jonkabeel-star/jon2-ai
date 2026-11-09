"""Guarded local GGUF inference API for Jon2 AI.

The API launches a local llama.cpp server only when an owner explicitly enables
JON2_CHAT_RELEASE_APPROVED and the approved GGUF file is present. No hosted AI
provider is called; all inference stays on the machine running this service.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

MODEL_PATH = Path(os.getenv("JON2_GGUF_PATH", "/models/jon2-qwen35-2b-q4_k_m.gguf"))
LLAMA_SERVER_BIN = os.getenv("LLAMA_SERVER_BIN", "llama-server")
LLAMA_SERVER_HOST = "127.0.0.1"
LLAMA_SERVER_PORT = int(os.getenv("LLAMA_SERVER_PORT", "8081"))
LLAMA_SERVER_URL = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}"
MAX_HISTORY = 8


def release_approved() -> bool:
    return os.getenv("JON2_CHAT_RELEASE_APPROVED", "false").strip().lower() == "true"


def allowed_origins() -> list[str]:
    configured = os.getenv("JON2_ALLOWED_ORIGINS", "https://jonkabeel-star.github.io")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def build_messages(message: str, history: list[dict] | None = None) -> list[dict[str, str]]:
    """Build a bounded Arabic-first chat prompt for the local model."""
    system = (
        "أنت Jon2 AI، مساعد عربي مستقل. أجب باللغة العربية، وافهم اللهجة المصرية "
        "والعربية الفصحى. كن واضحًا وعمليًا وصادقًا. لا تخترع معلومات أو مصادر. "
        "إذا لم تعرف الإجابة فقل ذلك بوضوح. لا تكرر السؤال ولا تكمل دور المستخدم."
    )
    messages = [{"role": "system", "content": system}]
    valid_history = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            valid_history.append({"role": role, "content": content.strip()[:2000]})
    messages.extend(valid_history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": message.strip()})
    return messages


def local_health(timeout: float = 1.0) -> bool:
    try:
        with urlopen(f"{LLAMA_SERVER_URL}/health", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def start_model_process() -> subprocess.Popen | None:
    if not release_approved() or not MODEL_PATH.is_file():
        return None
    binary = shutil.which(LLAMA_SERVER_BIN)
    if not binary:
        raise RuntimeError(f"llama-server executable not found: {LLAMA_SERVER_BIN}")
    command = [
        binary,
        "--model", str(MODEL_PATH),
        "--host", LLAMA_SERVER_HOST,
        "--port", str(LLAMA_SERVER_PORT),
        "--ctx-size", os.getenv("JON2_CONTEXT_SIZE", "4096"),
        "--threads", os.getenv("JON2_CPU_THREADS", "2"),
        "--n-gpu-layers", "0",
        "--jinja",
    ]
    return subprocess.Popen(command, stdout=None, stderr=None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_process = None
    app.state.model_error = None
    if release_approved() and MODEL_PATH.is_file():
        try:
            app.state.model_process = start_model_process()
            for _ in range(90):
                process = app.state.model_process
                if process is None or process.poll() is not None:
                    app.state.model_error = "llama-server exited before becoming ready"
                    break
                if local_health():
                    break
                await asyncio.sleep(1)
            else:
                app.state.model_error = "llama-server readiness timeout"
        except Exception as error:
            app.state.model_error = str(error)
    try:
        yield
    finally:
        process = app.state.model_process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


app = FastAPI(
    title="Jon2 AI Local Qwen Runtime",
    description="Private local inference through a project-controlled GGUF model.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=MAX_HISTORY)
    session_id: str | None = Field(default=None, max_length=64)


@app.get("/")
def home():
    return {"project": "Jon2 AI", "service": "local Qwen runtime", "health": "/api/health"}


@app.get("/api/health/live")
def live():
    return {"project": "Jon2 AI", "status": "alive"}


@app.get("/api/health")
def health():
    approved = release_approved()
    process = getattr(app.state, "model_process", None)
    process_running = process is not None and process.poll() is None
    ready = approved and MODEL_PATH.is_file() and process_running and local_health()
    return {
        "project": "Jon2 AI",
        "status": "ready" if ready else "online",
        "runtime": "llama.cpp-local",
        "base_model_family": "Qwen3.5-2B",
        "model_file_present": MODEL_PATH.is_file(),
        "model_file_bytes": MODEL_PATH.stat().st_size if MODEL_PATH.is_file() else 0,
        "release_approved": approved,
        "model_process_running": process_running,
        "chat_ready": ready,
        "error": getattr(app.state, "model_error", None),
    }


@app.get("/api/health/ready")
def ready():
    snapshot = health()
    if not snapshot["chat_ready"]:
        raise HTTPException(status_code=503, detail=snapshot)
    return {"project": "Jon2 AI", "status": "ready", "chat_ready": True}


@app.post("/api/chat")
def chat(request: ChatRequest):
    snapshot = health()
    if not snapshot["chat_ready"]:
        raise HTTPException(
            status_code=503,
            detail="محادثة Jon2 لم تُفعّل بعد. يلزم وجود نموذج GGUF وتشغيله واجتياز مراجعة الجودة.",
        )
    session_id = request.session_id or str(uuid.uuid4())
    messages = build_messages(
        request.message,
        [item.model_dump() for item in request.history],
    )
    payload = json.dumps({
        "model": "jon2-qwen-arabic",
        "messages": messages,
        "temperature": 0.35,
        "top_p": 0.85,
        "max_tokens": 512,
        "stream": False,
    }).encode("utf-8")
    upstream = Request(
        f"{LLAMA_SERVER_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(upstream, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
        reply = result["choices"][0]["message"]["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("empty model response")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError) as error:
        raise HTTPException(status_code=503, detail="تعذر الحصول على إجابة من نموذج Jon2 المحلي.") from error
    return {
        "project": "Jon2 AI",
        "reply": reply.strip(),
        "session_id": session_id,
        "response_mode": "local_qwen_gguf",
    }
