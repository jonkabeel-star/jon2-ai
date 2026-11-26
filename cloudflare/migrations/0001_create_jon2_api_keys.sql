-- Jon2 API key store — Cloudflare D1
-- Store only SHA-256 hashes. The plaintext key is returned once at issuance.
CREATE TABLE IF NOT EXISTS jon2_api_keys (
  id TEXT PRIMARY KEY NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  key_prefix TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  scopes_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS jon2_api_keys_status_expiry_idx
  ON jon2_api_keys(status, expires_at);
