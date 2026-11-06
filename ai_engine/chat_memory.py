"""Persistent, private-by-session conversation memory for Jon2.

Stores actual user/assistant turns in SQLite and retrieves relevant past turns
with a transparent lexical ranking. This is memory, not a claim of model
training or semantic embedding quality.
"""
from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Iterable

DEFAULT_DB = Path.home() / ".jon2-ai" / "memory.sqlite3"
MAX_CONTENT_CHARS = 4000
MAX_MESSAGES_PER_SESSION = 500
STOPWORDS = {
    "في", "من", "على", "الى", "إلى", "عن", "مع", "ده", "دي", "دا", "هو",
    "هي", "انا", "أنا", "انت", "أنت", "كان", "كانت", "يكون", "اللي",
    "ما", "مش", "لا", "نعم", "هل", "ثم", "او", "أو", "كل", "بعد", "قبل",
    "this", "that", "with", "from", "have", "what", "when", "where",
}


def database_path() -> Path:
    raw = os.getenv("JON2_MEMORY_DB_PATH", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_DB


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(target), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize(path: Path | None = None) -> None:
    with _connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id, id DESC);
        """)


def _valid_session(session_id: str) -> str:
    value = str(session_id or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", value):
        raise ValueError("session_id must be a UUID.")
    return value


def add_message(session_id: str, role: str, content: str, path: Path | None = None) -> None:
    sid = _valid_session(session_id)
    if role not in {"user", "assistant"}:
        raise ValueError("Unsupported message role.")
    text = str(content or "").strip()
    if not text or len(text) > MAX_CONTENT_CHARS:
        raise ValueError("Message content is empty or too long.")
    initialize(path)
    with _connect(path) as db:
        db.execute("INSERT OR IGNORE INTO conversations(session_id) VALUES (?)", (sid,))
        db.execute(
            "INSERT INTO messages(session_id, role, content) VALUES (?,?,?)",
            (sid, role, text),
        )
        db.execute(
            """DELETE FROM messages WHERE session_id=? AND id NOT IN
               (SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?)""",
            (sid, sid, MAX_MESSAGES_PER_SESSION),
        )
        db.execute(
            "UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE session_id=?",
            (sid,),
        )


def recent_messages(session_id: str, limit: int = 8, path: Path | None = None) -> list[dict]:
    sid = _valid_session(session_id)
    initialize(path)
    with _connect(path) as db:
        rows = db.execute(
            "SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (sid, max(1, min(int(limit), 20))),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens = re.findall(r"[\u0621-\u064a\u0660-\u0669a-z0-9]{2,}", normalized)
    return {token for token in tokens if token not in STOPWORDS}


def relevant_memories(session_id: str, query: str, limit: int = 4, path: Path | None = None) -> list[dict]:
    sid = _valid_session(session_id)
    query_terms = _terms(query)
    if not query_terms:
        return []
    initialize(path)
    with _connect(path) as db:
        rows = db.execute(
            "SELECT role,content,id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 200",
            (sid,),
        ).fetchall()
    scored = []
    for row in rows:
        terms = _terms(row["content"])
        overlap = query_terms & terms
        if overlap:
            score = len(overlap) / max(1, len(query_terms) ** 0.5)
            scored.append((score, row["id"], row["role"], row["content"]))
    scored.sort(reverse=True)
    return [
        {"role": role, "content": content, "relevance": round(score, 3)}
        for score, _id, role, content in scored[:max(1, min(limit, 8))]
    ]


def clear_session(session_id: str, path: Path | None = None) -> None:
    sid = _valid_session(session_id)
    initialize(path)
    with _connect(path) as db:
        db.execute("DELETE FROM conversations WHERE session_id=?", (sid,))


def session_stats(session_id: str, path: Path | None = None) -> dict:
    sid = _valid_session(session_id)
    initialize(path)
    with _connect(path) as db:
        row = db.execute(
            "SELECT COUNT(*) AS count, MAX(created_at) AS last_message FROM messages WHERE session_id=?",
            (sid,),
        ).fetchone()
    return {"message_count": int(row["count"]), "last_message_at": row["last_message"]}


