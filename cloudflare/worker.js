const ALLOWED_ORIGINS = new Set([
  "https://jon2-ai.pages.dev",
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const KEY_PREFIX = "jon2_live_";
const ALLOWED_SCOPES = new Set(["api:read", "api:write"]);
const MAX_BODY_BYTES = 8192;
const SHA256_HEX_LENGTH = 64;

function json(payload, status = 200, origin = "") {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Vary": "Origin",
  };
  if (origin) headers["Access-Control-Allow-Origin"] = origin;
  return new Response(JSON.stringify(payload), { status, headers });
}

function allowedOrigin(request) {
  const origin = request.headers.get("Origin") || "";
  if (!origin) return "";
  return ALLOWED_ORIGINS.has(origin) ? origin : null;
}

function bytesToHex(bytes) {
  return Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, "0")).join("");
}

async function sha256(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return bytesToHex(digest);
}

// Both inputs must be fixed-size SHA-256 hex digests. The loop never exits early
// based on the first differing character.
function constantTimeDigestEqual(left, right) {
  if (typeof left !== "string" || typeof right !== "string" ||
      left.length !== SHA256_HEX_LENGTH || right.length !== SHA256_HEX_LENGTH ||
      !/^[0-9a-f]{64}$/i.test(left) || !/^[0-9a-f]{64}$/i.test(right)) {
    return false;
  }
  let difference = 0;
  for (let index = 0; index < SHA256_HEX_LENGTH; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function randomToken(byteLength = 32) {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const value of bytes) binary += String.fromCharCode(value);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function readJson(request) {
  const declaredLength = Number(request.headers.get("Content-Length") || 0);
  if (declaredLength > MAX_BODY_BYTES) throw Object.assign(new Error("request_too_large"), { status: 413 });
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    throw Object.assign(new Error("request_too_large"), { status: 413 });
  }
  try {
    const value = JSON.parse(raw || "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid");
    return value;
  } catch {
    throw Object.assign(new Error("invalid_json"), { status: 400 });
  }
}

async function masterAuthorized(request, env) {
  const configured = typeof env.JON2_MASTER_KEY === "string" ? env.JON2_MASTER_KEY : "";
  const authorization = request.headers.get("Authorization") || "";
  const supplied = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";

  // Fail closed for absent, malformed, or weak configuration. Hash a fixed dummy
  // value when configuration is invalid so comparison still uses fixed-size digests.
  const configuredValid = configured.length >= 32 &&
    configured === configured.trim() &&
    !/[\r\n]/.test(configured);
  const suppliedValid = supplied.length >= 32 &&
    supplied === supplied.trim() &&
    !/[\r\n]/.test(supplied);
  const configuredDigest = await sha256(configuredValid ? configured : "jon2-invalid-master-secret-dummy");
  const suppliedDigest = await sha256(suppliedValid ? supplied : "jon2-invalid-supplied-secret-dummy");
  const matches = constantTimeDigestEqual(configuredDigest, suppliedDigest);
  return configuredValid && suppliedValid && matches;
}

function requireDatabase(env) {
  if (!env.JON2_DB || typeof env.JON2_DB.prepare !== "function") {
    throw Object.assign(new Error("api_key_store_not_configured"), { status: 503 });
  }
  return env.JON2_DB;
}

function validKeyId(value) {
  return typeof value === "string" && /^[0-9a-f-]{36}$/i.test(value);
}

function isUnexpiredIsoDate(value, now = Date.now()) {
  if (typeof value !== "string" || value.length === 0) return false;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) && timestamp > now;
}

async function issueKey(request, env, origin) {
  if (!await masterAuthorized(request, env)) return json({ error: "admin_unauthorized" }, 401, origin);
  const body = await readJson(request);
  const label = typeof body.label === "string" ? body.label.trim().slice(0, 80) : "";
  const requestedScopes = body.scopes === undefined ? ["api:read"] : body.scopes;
  if (!Array.isArray(requestedScopes) || requestedScopes.length < 1 || requestedScopes.length > 2 ||
      requestedScopes.some(scope => typeof scope !== "string" || !ALLOWED_SCOPES.has(scope)) ||
      new Set(requestedScopes).size !== requestedScopes.length) {
    return json({ error: "invalid_scopes", allowed: Array.from(ALLOWED_SCOPES) }, 400, origin);
  }
  const expirationDays = body.expirationDays === undefined ? 365 : body.expirationDays;
  if (!Number.isInteger(expirationDays) || expirationDays < 1 || expirationDays > 3650) {
    return json({ error: "invalid_expiration_days" }, 400, origin);
  }

  const db = requireDatabase(env);
  const key = KEY_PREFIX + randomToken(32);
  const keyId = crypto.randomUUID();
  const keyHash = await sha256(key);
  const prefix = key.slice(0, 17);
  const expiresAt = new Date(Date.now() + expirationDays * 86400000).toISOString();
  await db.prepare(
    "INSERT INTO jon2_api_keys (id, key_hash, key_prefix, label, scopes_json, status, created_at, expires_at) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)"
  ).bind(keyId, keyHash, prefix, label, JSON.stringify(requestedScopes), new Date().toISOString(), expiresAt).run();

  return json({
    created: true,
    key: key,
    warning: "Copy this key now. It will not be shown again.",
    keyInfo: { id: keyId, prefix, label, scopes: requestedScopes, status: "active", expiresAt }
  }, 201, origin);
}

async function verifyKey(request, env, origin) {
  const body = await readJson(request);
  const key = typeof body.key === "string" ? body.key : "";
  if (key.length < 40 || key.length > 160 || !key.startsWith(KEY_PREFIX)) {
    return json({ valid: false, error: "invalid_key" }, 401, origin);
  }
  const db = requireDatabase(env);
  const keyHash = await sha256(key);
  const result = await db.prepare(
    "SELECT id, key_prefix, scopes_json, status, expires_at FROM jon2_api_keys WHERE key_hash = ? LIMIT 1"
  ).bind(keyHash).first();
  if (!result || result.status !== "active" || !isUnexpiredIsoDate(result.expires_at)) {
    return json({ valid: false, error: "invalid_or_expired_key" }, 401, origin);
  }
  let scopes;
  try {
    scopes = JSON.parse(result.scopes_json);
    if (!Array.isArray(scopes) || scopes.length < 1 ||
        scopes.some(scope => typeof scope !== "string" || !ALLOWED_SCOPES.has(scope))) {
      throw new Error("invalid scopes");
    }
  } catch {
    return json({ valid: false, error: "invalid_key_record" }, 503, origin);
  }
  return json({
    valid: true,
    keyInfo: { id: result.id, prefix: result.key_prefix, scopes, expiresAt: result.expires_at }
  }, 200, origin);
}

async function revokeKey(request, env, origin) {
  if (!await masterAuthorized(request, env)) return json({ error: "admin_unauthorized" }, 401, origin);
  const body = await readJson(request);
  if (!validKeyId(body.keyId)) return json({ error: "invalid_key_id" }, 400, origin);
  const db = requireDatabase(env);
  const result = await db.prepare(
    "UPDATE jon2_api_keys SET status = 'revoked', revoked_at = ? WHERE id = ? AND status = 'active'"
  ).bind(new Date().toISOString(), body.keyId).run();
  const changed = Number(result.meta && result.meta.changes) || 0;
  return json({ revoked: changed === 1, keyId: body.keyId }, changed === 1 ? 200 : 404, origin);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();
    const origin = allowedOrigin(request);

    if (origin === null) {
      return json({ project: "Jon2 Cloud", error: "origin_not_allowed" }, 403);
    }

    if (method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          ...(origin ? { "Access-Control-Allow-Origin": origin } : {}),
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
          "Access-Control-Max-Age": "86400",
          "Vary": "Origin",
        },
      });
    }

    try {
      if (method === "POST" && path === "/api/keys/issue") {
        return await issueKey(request, env, origin);
      }
      if (method === "POST" && path === "/api/keys/verify") {
        return await verifyKey(request, env, origin);
      }
      if (method === "POST" && path === "/api/keys/revoke") {
        return await revokeKey(request, env, origin);
      }
    } catch (error) {
      const status = Number.isInteger(error.status) ? error.status : 503;
      const safeError = status === 400 || status === 413 ? error.message : "api_key_service_unavailable";
      return json({ error: safeError }, status, origin);
    }

    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return json({
        project: "Jon2 Cloud",
        status: "alive",
        service: "edge-gateway",
        model_runtime: "original_jon2_not_connected",
      }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      return json({
        project: "Jon2 Cloud",
        status: "online",
        api_ready: true,
        model_ready: false,
        chat_ready: false,
        inference_tested: false,
        model_status: "original_model_runtime_not_connected",
        model: "Jon2 Original Transformer",
        model_type: "project_owned_checkpoint_required",
        message: "عقل Jon2 غير جاهز للرد",
      }, 200, origin);
    }

    if (method === "POST" && path === "/api/chat") {
      return json({
        project: "Jon2 Cloud",
        error: "local_model_not_loaded",
        chat_ready: false,
        message: "عقل Jon2 غير جاهز للرد",
      }, 503, origin);
    }

    return json({ project: "Jon2 Cloud", error: "not_found" }, 404, origin);
  },
};
