"""Local SQLite conversation history and session-scoped, explicitly saved facts."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


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

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session_id_id ON messages(session_id, id);
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(facts)")}
            if columns and "session_id" not in columns:
                db.execute("ALTER TABLE facts RENAME TO facts_legacy")
                columns = set()
            if not columns:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS facts (
                        session_id TEXT NOT NULL,
                        fact_key TEXT NOT NULL,
                        fact_value TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                        PRIMARY KEY(session_id, fact_key)
                    )
                """)
            legacy_exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facts_legacy'"
            ).fetchone()
            if legacy_exists:
                db.execute("""
                    INSERT OR IGNORE INTO facts(session_id, fact_key, fact_value, updated_at)
                    SELECT '', fact_key, fact_value, updated_at FROM facts_legacy
                """)
                db.execute("DROP TABLE facts_legacy")

    def add_message(self, session_id: str, role: str, content: str) -> int:
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
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

    def save_fact(self, key: str, value: str, session_id: str = "") -> None:
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError("fact key and value must not be empty")
        with self._connect() as db:
            db.execute(
                "INSERT INTO facts(session_id, fact_key, fact_value) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id, fact_key) DO UPDATE SET fact_value=excluded.fact_value, "
                "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
                (session_id, key, value),
            )

    def facts(self, session_id: str = "") -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT fact_key, fact_value, updated_at FROM facts "
                "WHERE session_id = ? ORDER BY fact_key",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_fact(self, key: str, session_id: str = "") -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM facts WHERE session_id = ? AND fact_key = ?",
                (session_id, key.strip()),
            )
            return cursor.rowcount > 0

    def clear_session(self, session_id: str) -> int:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            return int(cursor.rowcount)
