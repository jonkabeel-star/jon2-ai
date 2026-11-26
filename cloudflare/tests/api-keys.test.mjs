import test from "node:test";
import assert from "node:assert/strict";
import worker from "../worker.js";

function makeEnv() {
  const records = new Map();
  const db = {
    prepare(sql) {
      return {
        values: [],
        bind(...values) { this.values = values; return this; },
        async run() {
          if (sql.startsWith("INSERT INTO jon2_api_keys")) {
            const [id, key_hash, key_prefix, label, scopes_json, status, created_at, expires_at] = this.values;
            records.set(key_hash, { id, key_prefix, label, scopes_json, status, created_at, expires_at });
            return { meta: { changes: 1 } };
          }
          if (sql.startsWith("UPDATE jon2_api_keys")) {
            const [revoked_at, id] = this.values;
            for (const record of records.values()) {
              if (record.id === id && record.status === "active") {
                record.status = "revoked";
                record.revoked_at = revoked_at;
                return { meta: { changes: 1 } };
              }
            }
            return { meta: { changes: 0 } };
          }
          throw new Error("Unexpected SQL in test");
        },
        async first() {
          const [hash] = this.values;
          return records.get(hash) || null;
        }
      };
    }
  };
  return { env: { JON2_DB: db, JON2_MASTER_KEY: "test-master-secret-value-which-is-long-enough" }, records };
}

async function call(env, path, body, headers = {}) {
  return worker.fetch(new Request("https://worker.example" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body)
  }), env);
}

test("issue, verify, and revoke are owner-gated and store only a hash", async () => {
  const { env, records } = makeEnv();
  const denied = await call(env, "/api/keys/issue", {});
  assert.equal(denied.status, 401);

  const issued = await call(env, "/api/keys/issue", { label: "test", scopes: ["api:read"] }, {
    Authorization: "Bearer " + env.JON2_MASTER_KEY
  });
  assert.equal(issued.status, 201);
  const payload = await issued.json();
  assert.match(payload.keyInfo.prefix, /^jon2_live_/);
  assert.equal(typeof payload.key, "string");
  assert.equal(records.size, 1);
  assert.equal(records.has(payload.key), false);

  const verified = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(verified.status, 200);
  assert.equal((await verified.json()).valid, true);

  const revoked = await call(env, "/api/keys/revoke", { keyId: payload.keyInfo.id }, {
    Authorization: "Bearer " + env.JON2_MASTER_KEY
  });
  assert.equal(revoked.status, 200);

  const rejected = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(rejected.status, 401);
});

test("unknown scopes and invalid expiration are rejected", async () => {
  const { env } = makeEnv();
  const headers = { Authorization: "Bearer " + env.JON2_MASTER_KEY };
  assert.equal((await call(env, "/api/keys/issue", { scopes: ["admin"] }, headers)).status, 400);
  assert.equal((await call(env, "/api/keys/issue", { expirationDays: 0 }, headers)).status, 400);
});

test("chat remains unavailable and does not consume API keys", async () => {
  const { env } = makeEnv();
  const response = await worker.fetch(new Request("https://worker.example/api/chat", { method: "POST" }), env);
  assert.equal(response.status, 503);
});
