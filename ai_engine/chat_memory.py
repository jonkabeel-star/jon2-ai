"""Persistent, private-by-session conversation memory for Jon2.

Stores actual user/assistant turns in SQLite. Retrieval uses a bounded,
Arabic-normalized BM25-style lexical ranker; it is not semantic embedding
search and does not train or modify model weights.
"""
from __future__ import annotations

import math
import os
import re
import sqlite3
import unicodedata
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = Path.home() / ".jon2-ai" / "memory.sqlite3"
MAX_CONTENT_CHARS = 4000
MAX_MESSAGES_PER_SESSION = 500
RETRIEVAL_SCAN_LIMIT = 200
RECENT_CONTEXT_RESERVE = 8
STOPWORDS = {
    "في", "من", "على", "الى", "إلى", "عن", "مع", "ده", "دي", "دا", "هو",
    "هي", "انا", "أنا", "انت", "أنت", "كان", "كانت", "يكون", "اللي",
    "ما", "مش", "لا", "نعم", "هل", "ثم", "او", "أو", "كل", "بعد", "قبل",
    "this", "that", "with", "from", "have", "what", "when", "where",
}


def database_path() -> Path:
    raw = os.getenv("JON2_MEMORY_DB_PATH", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_DB


@contextmanager
def _connect(path: Path | None = None):
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(target), timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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


def _normalize_arabic(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    normalized = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", normalized)
    return normalized.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي",
    }))


_NORMALIZED_STOPWORDS = {_normalize_arabic(word) for word in STOPWORDS}


def _terms(text: str) -> list[str]:
    normalized = _normalize_arabic(text)
    tokens = re.findall(r"[\u0621-\u064a\u0660-\u0669a-z0-9]{2,}", normalized)
    return [token for token in tokens if token not in _NORMALIZED_STOPWORDS]


def _rank_memory(query_terms: list[str], document_terms: list[str],
                 document_frequency: Counter, document_count: int,
                 recency: float, exact_phrase: bool) -> float:
    """A small BM25-style score with bounded recency and phrase boosts."""
    frequencies = Counter(document_terms)
    doc_length = len(document_terms)
    average_length = max(1.0, sum(document_frequency.values()) / max(1, document_count))
    score = 0.0
    for term in set(query_terms):
        frequency = frequencies.get(term, 0)
        if not frequency:
            continue
        df = document_frequency[term]
        inverse_frequency = math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
        length_norm = frequency * 2.2 / (
            frequency + 1.2 * (0.25 + 0.75 * doc_length / average_length)
        )
        score += inverse_frequency * length_norm
    if exact_phrase:
        score *= 1.35
    return score * (1.0 + 0.12 * recency)


def relevant_memories(session_id: str, query: str, limit: int = 4,
                       path: Path | None = None) -> list[dict]:
    """Retrieve older long-term turns, excluding the recent window already sent as history."""
    sid = _valid_session(session_id)
    query_terms = _terms(query)
    if not query_terms:
        return []
    initialize(path)
    with _connect(path) as db:
        rows = db.execute(
            "SELECT role,content,id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (sid, RETRIEVAL_SCAN_LIMIT),
        ).fetchall()

    # Recent turns are already supplied separately to the model; don't duplicate them.
    candidates = rows[RECENT_CONTEXT_RESERVE:]
    if not candidates:
        return []

    tokenized = [_terms(row["content"]) for row in candidates]
    document_frequency = Counter()
    for terms in tokenized:
        document_frequency.update(set(terms))
    document_count = len(candidates)
    normalized_query = " ".join(_normalize_arabic(query).split())
    scored = []
    for index, (row, terms) in enumerate(zip(candidates, tokenized)):
        if not terms:
            continue
        normalized_content = " ".join(_normalize_arabic(row["content"]).split())
        recency = 1.0 - index / max(1, document_count - 1)
        score = _rank_memory(
            query_terms, terms, document_frequency, document_count,
            recency, normalized_query in normalized_content,
        )
        if score > 0:
            scored.append((score, int(row["id"]), row["role"], row["content"]))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [
        {"role": role, "content": content, "relevance": round(score, 4)}
        for score, _id, role, content in scored[:max(1, min(int(limit), 8))]
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
