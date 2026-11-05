import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from chat_engine import generate_reply, model_is_ready
from external_models.jais2_routes import router as jais2_router
from compute.routes import router as compute_router

app = FastAPI(
    title="Jon2 AI API",
    description="API for the original, project-owned Jon2 language model.",
    version="1.2.0",
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
    allow_methods=["GET", "POST", "OPTIONS"],
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


@app.get("/")
def home():
    return {
        "project": "Jon2 AI",
        "status": "api_online",
        "model": "Jon2 Original Transformer",
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
    """Process liveness only; deliberately independent of model readiness."""
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
    }


@app.get("/api/health/ready")
def readiness():
    """Readiness for user-facing chat, not merely process liveness."""
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
        reply = generate_reply(message, [item.model_dump() for item in request.history])
        return {"project": "Jon2 AI", "reply": reply}
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
