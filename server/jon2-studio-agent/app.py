from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("JON2_AGENT_DB", str(APP_DIR / "memory.sqlite3")))
API_TOKEN = os.getenv("JON2_AGENT_TOKEN", "")
MODEL_BASE_URL = os.getenv("JON2_MODEL_BASE_URL", "").rstrip("/")
MODEL_NAME = os.getenv("JON2_MODEL_NAME", "")
MODEL_TIMEOUT = max(10, int(os.getenv("JON2_MODEL_TIMEOUT", "120")))
MAX_FILES = 40
MAX_FILE_CHARS = 80_000
MAX_TOTAL_CHARS = 300_000
MAX_PROMPT_CHARS = 8_000

app = FastAPI(title="Jon2 Studio Agent API", version="0.1.0")
allowed_origins = [x.strip() for x in os.getenv("JON2_AGENT_ORIGINS", "http://localhost:8788,http://127.0.0.1:8788").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class ProjectFile(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(max_length=MAX_FILE_CHARS)


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)
    message: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    active_file: str | None = Field(default=None, max_length=100)
    files: list[ProjectFile] = Field(default_factory=list, max_length=MAX_FILES)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str
    memory_turns: int


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user','assistant')),
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, id)")
    return con


def require_token(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN:
        raise HTTPException(status_code=503, detail="Server setup incomplete: set JON2_AGENT_TOKEN.")
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not supplied or not __import__("hmac").compare_digest(supplied, API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid agent token.")


def safe_project_context(files: list[ProjectFile], active_file: str | None) -> str:
    chunks: list[str] = []
    total = 0
    for item in files:
        name = item.name.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", name):
            continue
        if any(part in name.lower() for part in (".env", "secret", "credential", "token", "private_key")):
            continue
        content = item.content[:MAX_FILE_CHARS]
        if total + len(content) > MAX_TOTAL_CHARS:
            break
        total += len(content)
        chunks.append(f"\n--- FILE: {name} {'(ACTIVE)' if name == active_file else ''} ---\n{content}")
    return "\n".join(chunks) or "(No project files supplied.)"


def call_model(messages: list[dict[str, str]]) -> str:
    if not MODEL_BASE_URL or not MODEL_NAME:
        raise HTTPException(status_code=503, detail="No language model configured. Set JON2_MODEL_BASE_URL and JON2_MODEL_NAME.")
    url = MODEL_BASE_URL + "/chat/completions"
    payload = json.dumps({
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2500,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=MODEL_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
        answer = data["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty model response")
        return answer.strip()
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Model server returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Could not get a valid response from the configured model server.") from exc


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "Jon2 Studio Agent API",
        "status": "online",
        "model_configured": bool(MODEL_BASE_URL and MODEL_NAME),
        "authentication_configured": bool(API_TOKEN),
        "memory": "sqlite",
    }


@app.post("/v1/agent/chat", response_model=ChatResponse, dependencies=[Depends(require_token)])
def chat(body: ChatRequest) -> ChatResponse:
    session_id = body.session_id or str(uuid4())
    if not re.fullmatch(r"[A-Za-z0-9-]{8,80}", session_id):
        raise HTTPException(status_code=400, detail="Invalid session id.")

    context = safe_project_context(body.files, body.active_file)
    system = (
        "أنت Jon2 Bot، مهندس برمجيات مساعد. أجب بالعربية الواضحة ما لم يطلب المستخدم غير ذلك. "
        "افهم ملفات المشروع المرفقة قبل اقتراح أي تغيير. لا تدّع تنفيذ تعديل؛ أنت تقترح فقط في هذه الواجهة. "
        "لا تطلب الأسرار ولا تكشفها، ولا تنفذ أوامر نظام أو تنشر أو تعدّل GitHub. "
        "عند اقتراح كود، اذكر اسم الملف والتغيير بوضوح، وميّز بين الحقائق والافتراضات. "
        "إذا كانت معلومات المشروع غير كافية فاسأل سؤالًا محددًا. "
        "سياق المشروع الحالي:\n" + context
    )
    with db() as con:
        history = con.execute(
            "SELECT role, content FROM turns WHERE session_id=? ORDER BY id DESC LIMIT 20",
            (session_id,),
        ).fetchall()
        history.reverse()
        messages = [{"role": "system", "content": system}]
        messages.extend({"role": role, "content": content} for role, content in history)
        messages.append({"role": "user", "content": body.message})
        reply = call_model(messages)
        now = int(time.time())
        con.execute("INSERT INTO turns(session_id,role,content,created_at) VALUES(?,?,?,?)",
                    (session_id, "user", body.message, now))
        con.execute("INSERT INTO turns(session_id,role,content,created_at) VALUES(?,?,?,?)",
                    (session_id, "assistant", reply, now))
        con.commit()
        count = con.execute("SELECT COUNT(*) FROM turns WHERE session_id=?", (session_id,)).fetchone()[0]
    return ChatResponse(session_id=session_id, reply=reply, model=MODEL_NAME, memory_turns=count // 2)


@app.delete("/v1/agent/memory/{session_id}", dependencies=[Depends(require_token)])
def clear_memory(session_id: str) -> dict[str, str]:
    with db() as con:
        con.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
        con.commit()
    return {"status": "cleared", "session_id": session_id}
