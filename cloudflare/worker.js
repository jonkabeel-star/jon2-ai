const PROJECT = "Jon2 Cloud";
const ORIGINS = new Set([
  "https://jon2-ai.pages.dev",
  "https://feat-safari-persistent-model.jon2-ai.pages.dev",
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const MAX_BODY = 64 * 1024;

function json(data, status = 200, origin = "") {
  const headers = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "Vary": "Origin" };
  if (origin) headers["Access-Control-Allow-Origin"] = origin;
  return new Response(JSON.stringify(data), { status, headers });
}
function urlFor(env, path) {
  try {
    const base = new URL((env.JON2_RUNTIME_URL || "").trim());
    if (base.protocol !== "https:" || base.username || base.password) return null;
    return new URL(path, base);
  } catch { return null; }
}
function configured(env) {
  return Boolean(urlFor(env, "/v1/health") && typeof env.JON2_RUNTIME_TOKEN === "string" && env.JON2_RUNTIME_TOKEN.length >= 32);
}
function cors(origin) {
  return new Response(null, { status: 204, headers: {
    ...(origin ? { "Access-Control-Allow-Origin": origin } : {}),
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400", Vary: "Origin",
  }});
}
async function health(env) {
  if (!configured(env)) return { runtime_api_ready: false, model_ready: false, chat_ready: false, model_status: "runtime_not_configured" };
  try {
    const r = await fetch(urlFor(env, "/v1/health"), { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(8000) });
    const d = await r.json().catch(() => null);
    if (!r.ok || !d || typeof d !== "object") throw new Error("bad_health");
    return {
      runtime_api_ready: d.api_ready === true,
      model_ready: d.model_ready === true,
      chat_ready: d.chat_ready === true || d.model_ready === true,
      model_status: typeof d.model_status === "string" ? d.model_status : "unknown",
      inference_tested: d.inference_tested === true,
      quality_review_passed: d.quality_review_passed === true,
    };
  } catch (e) {
    return { runtime_api_ready: false, model_ready: false, chat_ready: false, model_status: e?.name === "TimeoutError" ? "runtime_timeout" : "runtime_unreachable" };
  }
}
function valid(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return false;
  if (typeof payload.message !== "string" || !payload.message.trim() || payload.message.length > 2000) return false;
  if (payload.history !== undefined && (!Array.isArray(payload.history) || payload.history.length > 8 ||
    !payload.history.every(x => x && typeof x === "object" && ["user", "assistant"].includes(x.role) &&
      typeof x.content === "string" && x.content.length <= 2000))) return false;
  return payload.session_id === undefined || (typeof payload.session_id === "string" && payload.session_id.length <= 64);
}
async function chat(request, origin, env) {
  if (!configured(env)) return json({ project: PROJECT, error: "model_runtime_not_connected", chat_ready: false,
    message: "إعدادات خادم Python أو سر الاتصال بمحرك Jon2 غير مكتملة. لن نستخدم نموذجًا بديلًا." }, 503, origin);
  if (!(request.headers.get("Content-Type") || "").toLowerCase().includes("application/json"))
    return json({ project: PROJECT, error: "unsupported_media_type", message: "أرسل الطلب بصيغة JSON." }, 415, origin);
  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY)
    return json({ project: PROJECT, error: "request_too_large", message: "حجم الطلب أكبر من الحد المسموح." }, 413, origin);
  let payload;
  try { payload = JSON.parse(raw); } catch {
    return json({ project: PROJECT, error: "invalid_json", message: "تعذّر قراءة بيانات المحادثة." }, 400, origin);
  }
  if (!valid(payload)) return json({ project: PROJECT, error: "invalid_chat_request", message: "طلب المحادثة غير صالح." }, 400, origin);
  try {
    const upstream = await fetch(urlFor(env, "/v1/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json", Authorization: "Bearer " + env.JON2_RUNTIME_TOKEN },
      body: JSON.stringify({ contract_version: "1", message: payload.message, history: (payload.history || []).slice(-8), session_id: payload.session_id }),
      signal: AbortSignal.timeout(60000),
    });
    const data = await upstream.json().catch(() => null);
    if (!upstream.ok) {
      const auth = upstream.status === 401 || upstream.status === 403;
      const timeout = upstream.status === 408 || upstream.status === 504;
      return json({ project: PROJECT, error: auth ? "runtime_unauthorized" : timeout ? "runtime_timeout" : "model_not_ready",
        chat_ready: false, message: auth ? "فشل التحقق من سر الاتصال بين Cloudflare ومحرك Jon2." :
          timeout ? "انتهت مهلة انتظار محرك Jon2." : "الخادم متصل، لكن نموذج Jon2 لم يجتز بوابة الجاهزية والجودة بعد." },
        auth ? 502 : timeout ? 504 : 503, origin);
    }
    if (!data || typeof data.reply !== "string" || !data.reply.trim())
      return json({ project: PROJECT, error: "invalid_runtime_response", message: "وصل رد غير صالح من محرك Jon2." }, 502, origin);
    return json({ project: PROJECT, api_version: "1", model: "Jon2 Original Transformer", reply: data.reply,
      session_id: data.session_id || payload.session_id || null }, 200, origin);
  } catch (e) {
    const timeout = e?.name === "TimeoutError" || e?.name === "AbortError";
    return json({ project: PROJECT, error: timeout ? "runtime_timeout" : "runtime_unreachable",
      message: timeout ? "انتهت مهلة انتظار محرك Jon2." : "تعذّر الوصول إلى خادم Jon2 الأصلي." }, timeout ? 504 : 503, origin);
  }
}
export default {
  async fetch(request, env = {}) {
    const u = new URL(request.url), path = u.pathname.replace(/\/+$/, "") || "/", method = request.method.toUpperCase();
    const rawOrigin = request.headers.get("Origin") || "";
    if (rawOrigin && !ORIGINS.has(rawOrigin)) return json({ project: PROJECT, error: "origin_not_allowed" }, 403);
    const origin = rawOrigin;
    if (method === "OPTIONS") return cors(origin);
    if (method === "GET" && (path === "/" || path === "/api/health/live"))
      return json({ project: PROJECT, status: "alive", service: "edge-gateway" }, 200, origin);
    if (method === "GET" && path === "/api/health") {
      const state = await health(env);
      return json({ project: PROJECT, status: "online", api_ready: true, ...state,
        message: state.chat_ready ? "محرك Jon2 الأصلي جاهز." :
          state.model_status === "runtime_not_configured" ? "بوابة Jon2 تعمل، لكن إعدادات الخادم الخاص غير مكتملة." :
          "خادم Jon2 متصل أو قيد الفحص، لكن المحادثة غير جاهزة بعد." }, 200, origin);
    }
    if (method === "POST" && path === "/api/chat") return chat(request, origin, env);
    return json({ project: PROJECT, error: "not_found" }, 404, origin);
  },
};
