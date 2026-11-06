import os
import re
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from chat_engine import generate_reply, model_is_ready
import chat_memory
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jonkabeel-star.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


def _checkpoint_configured() -> bool:
    checkpoint = os.getenv(
        "JON2_CHECKPOINT",
        os.path.join(os.path.dirname(__file__), "checkpoints", "jon2-small.pt"),
    )
    return os.path.isfile(checkpoint)


@app.get("/api/health/live")
def liveness():
    return {"project": "Jon2 AI", "status": "alive"}


@app.get("/api/health")
def health():
    loaded = model_is_ready()
    checkpoint_available = _checkpoint_configured()
    release_approved = _chat_release_approved()
    model_status = (
        "checkpoint_missing" if not checkpoint_available
        else "release_blocked" if not release_approved
        else "ready" if loaded
        else "checkpoint_available"
    )
    return {
        "project": "Jon2 AI",
        "status": "online",
        "api_version": app.version,
        "model": "Jon2 Original Transformer",
        "model_loaded": loaded,
        "checkpoint_configured": checkpoint_available,
        "chat_ready": release_approved and loaded and checkpoint_available,
        "release_approved": release_approved,
        "model_status": model_status,
        "chat_requires_model_checkpoint": True,
        "conversation_memory": "sqlite",
        "memory_retrieval": "arabic_normalized_bm25_lexical",
        "memory_recent_context_turns": 8,
        "memory_long_term_scan_limit": 200,
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
    if not _chat_release_approved():
        raise HTTPException(
            status_code=503,
            detail="محادثة Jon2 متوقفة حتى اعتماد جودة النموذج بعد المراجعة البشرية.",
        )
    try:
        history = [item.model_dump() for item in request.history]
        memories = []
        if request.session_id:
            # Read context before storing the current turn, preventing duplicate prompt entries.
            history = chat_memory.recent_messages(request.session_id, limit=8)
            memories = chat_memory.relevant_memories(request.session_id, message, limit=4)
            chat_memory.add_message(request.session_id, "user", message)
        reply = generate_reply(message, history, memories)
        if request.session_id:
            chat_memory.add_message(request.session_id, "assistant", reply)
        return {
            "project": "Jon2 AI",
            "reply": reply,
            "memory_used": bool(memories),
            "session_id": request.session_id,
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
