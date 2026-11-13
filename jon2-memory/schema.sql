PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memory_messages (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content TEXT NOT NULL CHECK (length(content) <= 12000),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memory_owner_session_time ON memory_messages(owner_id, session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_owner_time ON memory_messages(owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS memory_notes (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL CHECK (length(body) <= 12000),
  tags_json TEXT NOT NULL DEFAULT '[]',
  importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_notes_owner_updated ON memory_notes(owner_id, updated_at DESC);
