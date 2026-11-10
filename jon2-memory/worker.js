const json = (data, status = 200, extra = {}) => new Response(JSON.stringify(data), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra }
});
const makeId = () => crypto.randomUUID();
function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map(x => x.trim()).filter(Boolean);
  const h = { Vary: "Origin" };
  if (origin && allowed.includes(origin)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Headers"] = "Authorization, Content-Type";
    h["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS";
  }
  return h;
}
function validText(v, max = 12000) {
  return typeof v === "string" && v.trim().length > 0 && v.length <= max;
}
function authorized(request, env) {
  const expected = env.JON2_MEMORY_API_KEY;
  const supplied = (request.headers.get("Authorization") || "").replace(/^Bearer\\s+/i, "");
  return Boolean(expected && supplied && supplied === expected);
}
export default {
  async fetch(request, env) {
    const headers = corsHeaders(request, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") {
      try {
        await env.MEMORY_DB.prepare("SELECT 1 AS ok").first();
        return json({ service: "Jon2 Memory", status: "ready", storage: "Cloudflare D1", durable: true }, 200, headers);
      } catch {
        return json({ service: "Jon2 Memory", status: "database_unavailable" }, 503, headers);
      }
    }
    if (!authorized(request, env)) return json({ error: "unauthorized" }, 401, headers);
    try {
      if (url.pathname === "/v1/messages" && request.method === "POST") {
        const b = await request.json();
        if (!validText(b.owner_id, 128) || !validText(b.session_id, 128) ||
            !["user", "assistant", "system"].includes(b.role) || !validText(b.content)) {
          return json({ error: "invalid_message" }, 400, headers);
        }
        const messageId = makeId();
        const metadata = JSON.stringify(b.metadata && typeof b.metadata === "object" ? b.metadata : {});
        await env.MEMORY_DB.prepare(
          "INSERT INTO memory_messages (id, owner_id, session_id, role, content, metadata_json) VALUES (?, ?, ?, ?, ?, ?)"
        ).bind(messageId, b.owner_id.trim(), b.session_id.trim(), b.role, b.content.trim(), metadata).run();
        return json({ ok: true, id: messageId }, 201, headers);
      }
      if (url.pathname === "/v1/context" && request.method === "GET") {
        const owner = url.searchParams.get("owner_id") || "";
        const session = url.searchParams.get("session_id") || "";
        const limit = Math.min(Math.max(Number(url.searchParams.get("limit") || 20), 1), 50);
        if (!validText(owner, 128) || !validText(session, 128)) return json({ error: "invalid_scope" }, 400, headers);
        const result = await env.MEMORY_DB.prepare(
          "SELECT id, role, content, created_at FROM memory_messages WHERE owner_id = ? AND session_id = ? ORDER BY created_at DESC LIMIT ?"
        ).bind(owner, session, limit).all();
        return json({ ok: true, messages: (result.results || []).reverse() }, 200, headers);
      }
      if (url.pathname === "/v1/search" && request.method === "POST") {
        const b = await request.json();
        const owner = b.owner_id;
        if (!validText(owner, 128) || !validText(b.query, 300)) return json({ error: "invalid_search" }, 400, headers);
        const limit = Math.min(Math.max(Number(b.limit || 10), 1), 25);
        const terms = [...new Set(b.query.toLowerCase().split(/[^\\p{L}\\p{N}]+/u).filter(x => x.length > 1))].slice(0, 6);
        if (!terms.length) return json({ ok: true, memories: [] }, 200, headers);
        const clauses = terms.map(() => "lower(content) LIKE ?").join(" OR ");
        const binds = terms.map(term => "%" + term + "%");
        const sql = "SELECT id, session_id, role, content, created_at FROM memory_messages WHERE owner_id = ? AND (" + clauses + ") ORDER BY created_at DESC LIMIT ?";
        const result = await env.MEMORY_DB.prepare(sql).bind(owner, ...binds, limit).all();
        return json({ ok: true, memories: result.results || [] }, 200, headers);
      }
      if (url.pathname === "/v1/messages" && request.method === "DELETE") {
        const b = await request.json();
        if (!validText(b.owner_id, 128) || !validText(b.session_id, 128)) return json({ error: "invalid_scope" }, 400, headers);
        const result = await env.MEMORY_DB.prepare(
          "DELETE FROM memory_messages WHERE owner_id = ? AND session_id = ?"
        ).bind(b.owner_id, b.session_id).run();
        return json({ ok: true, deleted: result.meta?.changes || 0 }, 200, headers);
      }
      return json({ error: "not_found" }, 404, headers);
    } catch {
      return json({ error: "internal_error" }, 500, headers);
    }
  }
};
