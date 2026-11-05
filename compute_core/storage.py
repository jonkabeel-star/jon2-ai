"""Small persistent key/value storage for Jon2 Compute Core."""
import json
import sqlite3
from pathlib import Path
from typing import Any


class ComputeStorage:
    """SQLite-backed storage. The caller chooses where the database is stored."""

    def __init__(self, database_path: str = "jon2_compute_core.sqlite3") -> None:
        self.database_path = str(Path(database_path))
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def set(self, key: str, value: Any) -> None:
        if not isinstance(key, str) or not key or len(key) > 512:
            raise ValueError("key must be a non-empty string up to 512 characters")
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 1_000_000:
            raise ValueError("value exceeds 1 MB")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO kv_store(key, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, encoded),
            )

    def get(self, key: str, default: Any = None) -> Any:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM kv_store WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else default

    def delete(self, key: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM kv_store WHERE key = ?", (key,)
            )
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM kv_store"
            ).fetchone()[0])
