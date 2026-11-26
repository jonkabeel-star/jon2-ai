import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const workerSource = await readFile(fileURLToPath(new URL("../worker.js", import.meta.url)), "utf8");
const workerModule = await import("data:text/javascript;base64," + Buffer.from(workerSource).toString("base64"));
const worker = workerModule.default;
const MASTER = "test-master-secret-value-which-is-long-enough-for-tests";

function makeEnv(options = {}) {
  const records = new Map();
  const db = {
    prepare(sql) {
      return {
        values: [],
        bind(...values) { this.values = values; return this; },
        async run() {
          if (sql.startsWith("INSERT INTO jon2_api_keys")) {
            assert.match(sql, /VALUES \(\?, \?, \?, \?, \?, 'active', \?, \?\)/);
            const [id, key_hash, key_prefix, label, scopes_json, created_at, expires_at] = this.values;
            const createdAtMs = Date.parse(created_at);
            const expiresAtMs = Date.parse(expires_at);
            assert.ok(Number.isFinite(createdAtMs), "created_at must be a valid date");
            assert.ok(Number.isFinite(expiresAtMs), "expires_at must be a valid date");
            assert.ok(expiresAtMs > Date.now(), "expires_at must be in the future");
            records.set(key_hash, {
              id, key_prefix, label, scopes_json,
              status: "active",
              created_at,
              expires_at
            });
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
  return {
    env: {
      ...(options.withoutDb ? {} : { JON2_DB: db }),
      ...(options.master === undefined ? { JON2_MASTER_KEY: MASTER } :
        options.master === null ? {} : { JON2_MASTER_KEY: options.master })
    },
    records
  };
}

async function call(env, path, body, headers = {}) {
  return worker.fetch(new Request("https://worker.example" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body)
  }), env);
}

const adminHeaders = master => ({ Authorization: "Bearer " + master });

async function issue(env, overrides = {}, master = MASTER) {
  const response = await call(env, "/api/keys/issue", overrides, adminHeaders(master));
  const payload = await response.json();
  return { response, payload };
}

async function issueValidKey(env) {
  const { response, payload } = await issue(env, { scopes: ["api:read"] });
  assert.equal(response.status, 201);
  return payload;
}

test("D1 missing fails closed with 503", async () => {
  const { env } = makeEnv({ withoutDb: true });
  const response = await call(env, "/api/keys/verify", { key: "jon2_live_" + "a".repeat(48) });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error, "api_key_service_unavailable");
});

test("admin secret missing, weak, or incorrect is rejected with 401", async () => {
  const missing = makeEnv({ master: null });
  assert.equal((await call(missing.env, "/api/keys/issue", {})).status, 401);

  const weak = makeEnv({ master: "short" });
  assert.equal((await call(weak.env, "/api/keys/issue", {}, adminHeaders("short"))).status, 401);

  const { env } = makeEnv();
  assert.equal((await call(env, "/api/keys/issue", {}, adminHeaders("wrong-master-secret-value-that-is-long-enough"))).status, 401);
});

test("correct admin secret can issue a key", async () => {
  const { env, records } = makeEnv();
  const { response, payload } = await issue(env, { label: "owner-test", scopes: ["api:read"] });
  assert.equal(response.status, 201);
  assert.match(payload.key, /^jon2_live_/);
  assert.equal(records.size, 1);
  assert.equal(records.has(payload.key), false, "only the hash may be stored");
});

test("issued key is stored with active status and valid future timestamps", async () => {
  const { env, records } = makeEnv();
  const payload = await issueValidKey(env);
  const record = [...records.values()][0];

  assert.equal(records.size, 1);
  assert.equal(record.status, "active");
  assert.ok(Number.isFinite(Date.parse(record.created_at)));
  assert.ok(Number.isFinite(Date.parse(record.expires_at)));
  assert.ok(Date.parse(record.expires_at) > Date.now());
  assert.equal(record.id, payload.keyInfo.id);
});

test("valid subkey verifies and reports allowed scopes", async () => {
  const { env } = makeEnv();
  const payload = await issueValidKey(env);
  const response = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(response.status, 200);
  const result = await response.json();
  assert.equal(result.valid, true);
  assert.deepEqual(result.keyInfo.scopes, ["api:read"]);
});

test("revoked subkey is rejected", async () => {
  const { env } = makeEnv();
  const payload = await issueValidKey(env);
  const revoked = await call(env, "/api/keys/revoke", { keyId: payload.keyInfo.id }, adminHeaders(MASTER));
  assert.equal(revoked.status, 200);
  const verify = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(verify.status, 401);
});

test("expired subkey is rejected", async () => {
  const { env, records } = makeEnv();
  const payload = await issueValidKey(env);
  for (const record of records.values()) record.expires_at = new Date(Date.now() - 1000).toISOString();
  const verify = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(verify.status, 401);
});

test("expiry equal to current time is rejected", async () => {
  const { env, records } = makeEnv();
  const payload = await issueValidKey(env);
  const fixedNow = 1900000000000;
  for (const record of records.values()) record.expires_at = new Date(fixedNow).toISOString();
  const originalNow = Date.now;
  try {
    Date.now = () => fixedNow;
    const verify = await call(env, "/api/keys/verify", { key: payload.key });
    assert.equal(verify.status, 401);
  } finally {
    Date.now = originalNow;
  }
});

test("invalid and unparseable expiry is rejected", async () => {
  const { env, records } = makeEnv();
  const payload = await issueValidKey(env);
  for (const record of records.values()) record.expires_at = "not-a-date";
  const verify = await call(env, "/api/keys/verify", { key: payload.key });
  assert.equal(verify.status, 401);
});

test("unknown subkey is rejected", async () => {
  const { env } = makeEnv();
  const response = await call(env, "/api/keys/verify", { key: "jon2_live_" + "z".repeat(48) });
  assert.equal(response.status, 401);
});

test("disallowed scopes cannot be issued", async () => {
  const { env } = makeEnv();
  const { response } = await issue(env, { scopes: ["admin"] });
  assert.equal(response.status, 400);
});

test("duplicate scopes and invalid expiration are rejected", async () => {
  const { env } = makeEnv();
  assert.equal((await issue(env, { scopes: ["api:read", "api:read"] })).response.status, 400);
  assert.equal((await issue(env, { expirationDays: 0 })).response.status, 400);
});

test("chat remains unchanged and unavailable", async () => {
  const { env } = makeEnv();
  const response = await worker.fetch(new Request("https://worker.example/api/chat", { method: "POST" }), env);
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error, "local_model_not_loaded");
});
