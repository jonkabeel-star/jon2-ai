"""Local-only FastAPI test server for Jon2 Lite; independent of Cloudflare Worker."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .brain import respond
from .memory import LiteMemory

app = FastAPI(title="Jon2 Lite Local API", version="0.2.0")
memory = LiteMemory()


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = Field(default=None, max_length=100)


class FactInput(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="", max_length=100)


@app.get("/health")
def health() -> dict[str, object]:
    return {"service": "jon2-lite-local", "status": "ok", "model_ready": False,
            "model_integration": "not_configured", "storage": "local_sqlite"}


@app.post("/lite/chat")
def chat(payload: ChatInput) -> dict[str, object]:
    session_id = (payload.session_id or str(uuid.uuid4())).strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="invalid_session_id")
    memory.add_message(session_id, "user", payload.message)
    history = memory.history(session_id)
    reply = respond(payload.message, history=history[:-1], facts=memory.facts(session_id))
    memory.add_message(session_id, "assistant", reply.text)
    return {"session_id": session_id, "reply": reply.text, "intent": reply.intent,
            "language_style": reply.language_style, "model_used": reply.model_used}


@app.get("/lite/history")
def history(session_id: str = Query(min_length=1, max_length=100), limit: int = 50) -> dict[str, object]:
    return {"session_id": session_id, "messages": memory.history(session_id, limit)}


@app.delete("/lite/history")
def clear_history(session_id: str = Query(min_length=1, max_length=100)) -> dict[str, int]:
    return {"deleted_messages": memory.clear_session(session_id)}


@app.get("/lite/facts")
def facts(session_id: str = Query(default="", max_length=100)) -> dict[str, object]:
    return {"session_id": session_id, "facts": memory.facts(session_id)}


@app.put("/lite/facts")
def save_fact(payload: FactInput) -> dict[str, str]:
    memory.save_fact(payload.key, payload.value, payload.session_id)
    return {"saved": payload.key, "session_id": payload.session_id}


@app.delete("/lite/facts/{key}")
def delete_fact(key: str, session_id: str = Query(default="", max_length=100)) -> dict[str, object]:
    deleted = memory.delete_fact(key, session_id)
    return {"deleted": deleted, "key": key, "session_id": session_id}
