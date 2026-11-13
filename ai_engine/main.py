import os
import hmac
import re
from typing import Literal
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from chat_engine import generate_reply, load_runtime, model_is_ready
import chat_memory
from knowledge_engine import (
    format_knowledge_answer, local_greeting, local_identity, looks_like_fact_question,
    retrieve_knowledge,
)
from external_models.jais2_routes import router as jais2_router
from compute.routes import router as compute_router
from model_profiles import PROFILES, describe_profile, list_profiles

app = FastAPI(
    title="Jon2 AI API",
    description="API for the original, project-owned Jon2 language model with persistent conversation memory.",
    version="1.5.0",
)

app.include_router(jais2_router)
app.include_router(compute_router)


@app.on_event("startup")
def preload_original_jon2_model() -> None:
    """Optionally load the existing private checkpoint without opening chat."""
    if os.getenv("JON2_PRELOAD_MODEL", "false").strip().lower() != "true":
        return
    try:
        load_runtime()
        print("Jon2 original checkpoint loaded successfully; chat release gates remain unchanged.")
    except Exception as error:
        # Keep health endpoints available so the host can report the load failure.
        print(f"Jon2 original checkpoint preload failed: {type(error).__name__}: {error}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jonkabeel-star.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["1"] | None = None
    request_id: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    session_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
    )


class RuntimeV1ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"]
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    session_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
    )

@app.get("/")
def home():
    # Serve the actual website from the same Python process when packaged.
    # This makes the browser chat call this API's own origin without a second host.
    web_index = Path(__file__).resolve().parent.parent / "index.html"
    if web_index.is_file():
        return FileResponse(web_index, media_type="text/html")
    return {
        "project": "Jon2 AI",
        "status": "api_online",
        "model": "Jon2 Original Transformer",
        "memory": "SQLite persistent conversation memory",
        "health": "/api/health",
        "docs": "/docs",
    }


def _chat_release_approved() -> bool:
    """Require an explicit release decision after human quality review."""
    return os.getenv("JON2_CHAT_RELEASE_APPROVED", "false").strip().lower() == "true"


def _experimental_chat_enabled() -> bool:
    """Allow owner-approved trial replies with an explicit quality warning."""
    return os.getenv("JON2_EXPERIMENTAL_CHAT", "false").strip().lower() == "true"


def _checkpoint_configured() -> bool:
    checkpoint = os.getenv(
        "JON2_CHECKPOINT",
        os.path.join(os.path.dirname(__file__), "checkpoints", "jon2-small.pt"),
    )
    return os.path.isfile(checkpoint)


def _inference_tested() -> bool:
    return os.getenv("JON2_INFERENCE_TESTED", "false").strip().lower() == "true"


def _quality_review_passed() -> bool:
    return os.getenv("JON2_QUALITY_REVIEW_PASSED", "false").strip().lower() == "true"


def _public_release_ready() -> bool:
    """Single fail-closed gate shared by health and every chat route."""
    return (
        _chat_release_approved()
        and _checkpoint_configured()
        and model_is_ready()
        and _inference_tested()
        and _quality_review_passed()
    )


@app.get("/api/health/live")
def liveness():
    return {"project": "Jon2 AI", "status": "alive"}


@app.get("/api/health")
def health():
    loaded = model_is_ready()
    checkpoint_available = _checkpoint_configured()
    release_approved = _chat_release_approved()
    experimental = _experimental_chat_enabled() and not release_approved
    inference_tested = _inference_tested()
    quality_review_passed = _quality_review_passed()
    chat_enabled = (
        release_approved and loaded and checkpoint_available
        and inference_tested and quality_review_passed
    )
    model_status = (
        "checkpoint_missing" if not checkpoint_available
        else "checkpoint_available" if not loaded
        else "inference_not_tested" if not inference_tested
        else "human_quality_review_pending" if not quality_review_passed
        else "release_blocked" if not release_approved
        else "ready"
    )
    checkpoint_path = os.getenv(
        "JON2_CHECKPOINT",
        os.path.join(os.path.dirname(__file__), "checkpoints", "jon2-small.pt"),
    )
    checkpoint_size = os.path.getsize(checkpoint_path) if os.path.isfile(checkpoint_path) else 0
    checkpoint_readable = os.path.isfile(checkpoint_path) and os.access(checkpoint_path, os.R_OK)
    return {
        "project": "Jon2 AI",
        "status": "online",
        "api_version": app.version,
        "model": "Jon2 Original Transformer",
        "model_loaded": loaded,
        "model_type": "jon2_original",
        "inference_tested": inference_tested,
        "quality_review_passed": quality_review_passed,
        "checkpoint_configured": checkpoint_available,
        "checkpoint_readable": checkpoint_readable,
        "checkpoint_size_bytes": checkpoint_size,
        "checkpoint_path": checkpoint_path,
        "kaggle_token_present": bool(os.getenv("KAGGLE_API_TOKEN")),
        "experimental_chat_enabled": _experimental_chat_enabled(),
        "chat_ready": chat_enabled,
        "release_approved": release_approved,
        "experimental_mode": experimental,
        "model_status": model_status,
        "chat_requires_model_checkpoint": True,
        "conversation_memory": "sqlite",
        "knowledge_retrieval": "wikipedia_multilingual_with_english_fallback",
        "knowledge_cache": "sqlite",
        "knowledge_cache_ttl_seconds": 604800,
        "memory_retrieval": "arabic_normalized_bm25_lexical",
        "memory_recent_context_turns": 8,
        "memory_long_term_scan_limit": 200,
    }


@app.get("/v1/health")
def runtime_v1_health():
    """Expose the versioned runtime contract without implying model readiness."""
    snapshot = health()
    model_ready = bool(snapshot["chat_ready"])
    return {
        "contract_version": "1",
        "project": "Jon2 AI",
        "status": "ready" if model_ready else "online",
        "api_ready": len(os.getenv("JON2_RUNTIME_TOKEN", "")) >= 32,
        "model_ready": model_ready,
        "model_type": "jon2_original",
        "inference_tested": bool(snapshot["inference_tested"]),
        "quality_review_passed": bool(snapshot["quality_review_passed"]),
        "model_status": snapshot["model_status"],
    }


@app.post("/v1/chat")
def runtime_v1_chat(
    request: RuntimeV1ChatRequest,
    authorization: str | None = Header(default=None),
):
    """Adapt the versioned contract to the existing guarded Jon2 chat engine."""
    expected_token = os.getenv("JON2_RUNTIME_TOKEN", "")
    if len(expected_token) < 32:
        return JSONResponse(
            status_code=503,
            content={
                "contract_version": "1",
                "error": "runtime_auth_not_configured",
                "detail": "The private runtime authentication secret is not configured.",
            },
        )
    supplied_token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not supplied_token or not hmac.compare_digest(expected_token, supplied_token):
        return JSONResponse(
            status_code=401,
            content={
                "contract_version": "1",
                "error": "runtime_unauthorized",
                "detail": "Runtime authentication failed.",
            },
        )
    legacy_request = ChatRequest(
        message=request.message,
        history=request.history,
        session_id=request.session_id,
    )
    try:
        result = chat(legacy_request)
    except HTTPException as error:
        detail = error.detail if isinstance(error.detail, str) else "Runtime request failed."
        error_code = (
            "model_not_ready" if error.status_code == 503
            else "invalid_request" if error.status_code == 400
            else "runtime_error"
        )
        return JSONResponse(
            status_code=error.status_code,
            content={
                "contract_version": "1",
                "error": error_code,
                "detail": detail,
            },
        )

    reply = result.get("reply") if isinstance(result, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        return JSONResponse(
            status_code=503,
            content={
                "contract_version": "1",
                "error": "empty_model_reply",
                "detail": "The Jon2 runtime did not return a usable reply.",
            },
        )

    return {
        "contract_version": "1",
        "project": "Jon2 AI",
        "reply": reply,
        "session_id": result.get("session_id"),
    }

@app.get("/api/health/ready")
def readiness():
    snapshot = health()
    if not snapshot["chat_ready"]:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": snapshot["model_status"],
                "chat_ready": False,
            },
        )
    return {"project": "Jon2 AI", "status": "ready", "chat_ready": True}



@app.get("/api/model/profiles")
def model_profiles():
    """List architecture presets; this endpoint never allocates or trains a model."""
    return {
        "project": "Jon2 AI",
        "status": "configuration_only",
        "weights_created": False,
        "profiles": list_profiles(),
    }


@app.get("/api/model/profiles/{profile_name}")
def model_profile(profile_name: str):
    """Describe one known profile without starting a training job."""
    try:
        return {
            "project": "Jon2 AI",
            "status": "configuration_only",
            "weights_created": False,
            "profile": describe_profile(profile_name),
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/api/memory/{session_id}")
def memory_status(session_id: str):
    try:
        return {"project": "Jon2 AI", **chat_memory.session_stats(session_id)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.delete("/api/memory/{session_id}")
def clear_memory(session_id: str):
    try:
        chat_memory.clear_session(session_id)
        return {"project": "Jon2 AI", "cleared": True}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="اكتب رسالتك أولًا.")

    # Narrow local intents and attributed factual retrieval do not require
    # model weights. Web retrieval uses a free public encyclopedia API, not an AI API.
    identity = local_identity(message)
    if identity:
        if request.session_id:
            chat_memory.add_exchange(request.session_id, message, identity)
        return {
            "project": "Jon2 AI", "reply": identity, "memory_used": False,
            "session_id": request.session_id, "knowledge_used": False,
            "response_mode": "local_identity",
        }

    greeting = local_greeting(message)
    if greeting:
        if request.session_id:
            chat_memory.add_exchange(request.session_id, message, greeting)
        return {
            "project": "Jon2 AI", "reply": greeting, "memory_used": False,
            "session_id": request.session_id, "knowledge_used": False,
            "response_mode": "local_greeting",
        }

    if looks_like_fact_question(message):
        knowledge = retrieve_knowledge(message)
        if knowledge:
            reply = format_knowledge_answer(knowledge)
            if request.session_id:
                chat_memory.add_exchange(request.session_id, message, reply)
            return {
                "project": "Jon2 AI", "reply": reply, "memory_used": False,
                "session_id": request.session_id, "knowledge_used": True,
                "knowledge_cached": bool(knowledge.get("cached")),
                "knowledge_source": knowledge.get("source_url"),
                "response_mode": "source_retrieval",
            }

    # General free-form conversation remains protected until the original
    # checkpoint passes inference tests and explicit human quality approval.
    if not _public_release_ready():
        snapshot = health()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "public_release_gate_closed",
                "message": "المحادثة العامة تحتاج إلى نموذج Jon2 أصلي مجرّب ومراجَع قبل فتحها.",
                "model_status": snapshot["model_status"],
                "chat_ready": False,
            },
        )


    try:
        history = [item.model_dump() for item in request.history]
        memories = []
        if request.session_id:
            # Read context before storing the current turn, preventing duplicate prompt entries.
            history = chat_memory.recent_messages(request.session_id, limit=8)
            memories = chat_memory.relevant_memories(request.session_id, message, limit=4)
        reply = generate_reply(message, history, memories)
        if request.session_id:
            # Commit both sides only after generation succeeds; failed inference
            # must not leave an orphan user turn that repeats on the next request.
            chat_memory.add_exchange(request.session_id, message, reply)
        return {
            "project": "Jon2 AI",
            "reply": reply,
            "memory_used": bool(memories),
            "session_id": request.session_id,
            "experimental": _experimental_chat_enabled() and not _chat_release_approved(),
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        print(f"Jon2 AI chat error: {error}")
        raise HTTPException(
            status_code=503,
            detail="تعذر تشغيل نموذج Jon2 الأصلي. راجع سجلات الخادم.",
        )
