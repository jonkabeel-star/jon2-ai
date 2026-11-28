"""Local SQLite conversation history and explicitly saved facts."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def default_db_path() -> Path:
    configured = os.environ.get("JON2_LITE_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parent / "data" / "jon2_lite.sqlite3"


class LiteMemory:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
                    ON messages(session_id, id);
                CREATE TABLE IF NOT EXISTS facts (
                    fact_key TEXT PRIMARY KEY,
                    fact_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                """
            )

    def add_message(self, session_id: str, role: str, content: str) -> int:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            return int(cursor.lastrowid)

    def history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, session_id, role, content, created_at FROM messages "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def save_fact(self, key: str, value: str) -> None:
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError("fact key and value must not be empty")
        with self._connect() as db:
            db.execute(
                "INSERT INTO facts(fact_key, fact_value) VALUES (?, ?) "
                "ON CONFLICT(fact_key) DO UPDATE SET fact_value=excluded.fact_value, "
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
                (key, value),
            )

    def facts(self) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT fact_key, fact_value, updated_at FROM facts ORDER BY fact_key"
            ).fetchall()
        return [dict(row) for row in rows]
