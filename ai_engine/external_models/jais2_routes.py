"""Opt-in, separately gated API routes for Jon2 Arabic.

No model weights are loaded at import time. The route is disabled by default,
requires a private bearer token, and never contacts hosted inference services.
"""
from __future__ import annotations

import hmac
import os
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(tags=["Jon2 Arabic"])


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ArabicChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    max_new_tokens: int = Field(default=256, ge=1, le=512)


def _enabled() -> bool:
    return os.getenv("JON2_JAIS2_API_ENABLED", "false").strip().lower() == "true"


def _configured_token() -> str:
    return os.getenv("JON2_JAIS2_API_TOKEN", "").strip()


def _authorize(authorization: str | None) -> None:
    expected = _configured_token()
    if not expected:
        raise HTTPException(status_code=503, detail="Jon2 Arabic API token is not configured.")
    supplied = (authorization or "").strip()
    scheme, _, token = supplied.partition(" ")
    if scheme.lower() != "bearer" or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized.")


@router.get("/api/jais2/health")
def jais2_health():
    if not _enabled():
        return {"project": "Jon2 Arabic", "status": "disabled", "model_loaded": False}
    # Import only after opt-in; this does not load model weights.
    from external_models import jais2_runtime

    return {
        "project": "Jon2 Arabic",
        "status": "ready" if jais2_runtime.model_is_ready() else "enabled_not_loaded",
        "model_loaded": jais2_runtime.model_is_ready(),
        "local_checkpoint_configured": bool(os.getenv("JON2_JAIS2_LOCAL_PATH", "").strip()),
    }


@router.post("/api/jais2/chat")
def jais2_chat(
    request: ArabicChatRequest,
    authorization: str | None = Header(default=None),
):
    if not _enabled():
        raise HTTPException(status_code=503, detail="Jon2 Arabic API is disabled.")
    _authorize(authorization)

    from external_models import jais2_runtime

    try:
        reply = jais2_runtime.generate_reply(
            request.message,
            [item.model_dump() for item in request.history],
            max_new_tokens=request.max_new_tokens,
        )
        return {"project": "Jon2 Arabic", "reply": reply, "model": jais2_runtime.MODEL_ID}
    except (FileNotFoundError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
