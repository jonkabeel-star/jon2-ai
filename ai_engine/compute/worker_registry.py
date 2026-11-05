"""Authenticated, SQLite-backed registry for real Jon2 Compute workers.

Worker enrollment is disabled unless a strong owner token is configured.
Worker credentials are returned once and only SHA-256 hashes are persisted.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

NODE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
DEFAULT_DB = "/tmp/jon2-compute/workers.sqlite3"


def _db_path() -> str:
    return os.getenv("JON2_COMPUTE_DB_PATH", DEFAULT_DB)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def initialize() -> None:
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                node_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                cpu_count INTEGER NOT NULL,
                memory_total_bytes INTEGER NOT NULL,
                accelerator_types TEXT NOT NULL,
                accelerator_names TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_seen REAL NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS workers_last_seen_idx ON workers(last_seen)")


def owner_token_configured() -> bool:
    token = os.getenv("JON2_COMPUTE_OWNER_TOKEN", "")
    return len(token) >= 32


def verify_owner_token(candidate: str | None) -> bool:
    expected = os.getenv("JON2_COMPUTE_OWNER_TOKEN", "")
    if len(expected) < 32 or not candidate:
        return False
    import hmac
    return hmac.compare_digest(expected, candidate)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def _validate_accelerator_values(values: list[str]) -> None:
    if not isinstance(values, list) or len(values) > 8:
        raise ValueError("Too many accelerator entries.")
    for value in values:
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise ValueError("Accelerator entries must be non-empty strings up to 100 characters.")
        if "," in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Accelerator entries cannot contain commas or control characters.")

def enroll(node_id: str, display_name: str, platform: str,
           cpu_count: int, memory_total_bytes: int,
           accelerator_types: list[str], accelerator_names: list[str]) -> str:
    if not NODE_ID_RE.fullmatch(node_id):
        raise ValueError("node_id must be 3-64 safe characters.")
    if not 1 <= cpu_count <= 4096:
        raise ValueError("cpu_count is outside the accepted range.")
    if not 0 <= memory_total_bytes <= 2**60:
        raise ValueError("memory_total_bytes is outside the accepted range.")
    if len(display_name) > 80 or len(platform) > 80:
        raise ValueError("display_name or platform is too long.")
    _validate_accelerator_values(accelerator_types)
    _validate_accelerator_values(accelerator_names)
    token = secrets.token_urlsafe(48)
    now = time.time()
    with _connect() as db:
        db.execute("""
            INSERT INTO workers (
                node_id, token_hash, display_name, platform, cpu_count,
                memory_total_bytes, accelerator_types, accelerator_names,
                status, created_at, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'online', ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                token_hash=excluded.token_hash,
                display_name=excluded.display_name,
                platform=excluded.platform,
                cpu_count=excluded.cpu_count,
                memory_total_bytes=excluded.memory_total_bytes,
                accelerator_types=excluded.accelerator_types,
                accelerator_names=excluded.accelerator_names,
                status='online',
                last_seen=excluded.last_seen
        """, (
            node_id, _token_hash(token), display_name, platform, cpu_count,
            memory_total_bytes, ",".join(accelerator_types),
            ",".join(accelerator_names), now, now
        ))
    return token


def authenticate_worker(node_id: str, token: str | None) -> bool:
    if not token:
        return False
    with _connect() as db:
        row = db.execute(
            "SELECT token_hash, status FROM workers WHERE node_id=?", (node_id,)
        ).fetchone()
    if not row or row["status"] != "online":
        return False
    import hmac
    return hmac.compare_digest(row["token_hash"], _token_hash(token))


def heartbeat(node_id: str, token: str, cpu_count: int,
              memory_total_bytes: int, accelerator_types: list[str],
              accelerator_names: list[str]) -> bool:
    if not 1 <= cpu_count <= 4096 or not 0 <= memory_total_bytes <= 2**60:
        raise ValueError("Worker capacity values are outside accepted ranges.")
    _validate_accelerator_values(accelerator_types)
    _validate_accelerator_values(accelerator_names)
    if not authenticate_worker(node_id, token):
        return False
    with _connect() as db:
        result = db.execute("""
            UPDATE workers SET cpu_count=?, memory_total_bytes=?,
                accelerator_types=?, accelerator_names=?, last_seen=?
            WHERE node_id=? AND token_hash=? AND status='online'
        """, (
            cpu_count, memory_total_bytes, ",".join(accelerator_types),
            ",".join(accelerator_names), time.time(), node_id, _token_hash(token)
        ))
        return result.rowcount == 1


def list_workers(stale_after_seconds: int = 120) -> list[dict[str, Any]]:
    now = time.time()
    with _connect() as db:
        rows = db.execute("SELECT * FROM workers ORDER BY node_id").fetchall()
    result = []
    for row in rows:
        is_online = row["status"] == "online" and now - row["last_seen"] <= stale_after_seconds
        result.append({
            "node_id": row["node_id"],
            "display_name": row["display_name"],
            "platform": row["platform"],
            "cpu_count": row["cpu_count"],
            "memory_total_bytes": row["memory_total_bytes"],
            "accelerator_types": [x for x in row["accelerator_types"].split(",") if x],
            "accelerator_names": [x for x in row["accelerator_names"].split(",") if x],
            "status": "online" if is_online else "stale_or_revoked",
            "created_at": row["created_at"],
            "last_seen": row["last_seen"],
            "age_seconds": max(0, int(now - row["last_seen"])),
        })
    return result


def revoke(node_id: str) -> bool:
    with _connect() as db:
        result = db.execute(
            "UPDATE workers SET status='revoked' WHERE node_id=?", (node_id,)
        )
        return result.rowcount == 1
