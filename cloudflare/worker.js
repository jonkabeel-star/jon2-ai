const ALLOWED_ORIGINS = new Set([
  "https://jonkabeel-star.github.io",
  "https://jon2-ai.pages.dev",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const PROJECT = "Jon2 Cloud";
const MAX_BODY_BYTES = 64 * 1024;
const RUNTIME_TIMEOUT_MS = 60_000;

function json(payload, status = 200, origin = "") {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Vary": "Origin",
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
  }
  return new Response(JSON.stringify(payload), { status, headers });
}

function runtimeUrl(env, path) {
  const configured = String(env.JON2_RUNTIME_URL || "").trim();
  if (!configured) return null;
  try {
    const base = new URL(configured);
    if (base.protocol !== "https:" || base.username || base.password ||
        base.search || base.hash || base.pathname !== "/") return null;
    return new URL(path, base);
  } catch {
    return null;
  }
}

function runtimeConfigured(env) {
  return Boolean(
    runtimeUrl(env, "/v1/chat") &&
    typeof env.JON2_RUNTIME_TOKEN === "string" &&
    env.JON2_RUNTIME_TOKEN.length >= 32
  );
}

async function readRuntimeHealth(env) {
  if (!runtimeConfigured(env)) {
    return { api_ready: false, model_ready: false, public_chat_ready: false,
      model_status: "not_connected" };
  }
  try {
    const response = await fetch(runtimeUrl(env, "/v1/health"), {
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(8_000),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data || typeof data !== "object") {
      return { api_ready: false, model_ready: false, public_chat_ready: false,
        model_status: "runtime_error" };
    }
    const modelReady = data.model_ready === true;
    const publicChatReady =
      modelReady &&
      data.inference_tested === true &&
      data.quality_review_passed === true &&
      data.public_chat_enabled === true &&
      env.JON2_PUBLIC_CHAT_ENABLED === "true";
    return {
      api_ready: true,
      model_ready: modelReady,
      public_chat_ready: publicChatReady,
      model_status: publicChatReady ? "ready" :
        modelReady ? "human_review_or_release_pending" :
        (typeof data.model_status === "string" ? data.model_status : "not_ready"),
    };
  } catch {
    return { api_ready: false, model_ready: false, public_chat_ready: false,
      model_status: "runtime_unreachable" };
  }
}

async function handleChat(request, origin, env) {
  const health = await readRuntimeHealth(env);
  if (!health.public_chat_ready) {
    return json({
      project: PROJECT,
      error: "model_not_released",
      message: "محرك Jon2 لم يجتز اختبارات التشغيل ومراجعة الجودة أو لم تتم الموافقة على فتحه بعد.",
      chat_ready: false,
      model_status: health.model_status,
    }, 503, origin);
  }

  const length = Number(request.headers.get("Content-Length") || "0");
  if (Number.isFinite(length) && length > MAX_BODY_BYTES) {
    return json({ project: PROJECT, error: "request_too_large",
      message: "حجم طلب المحادثة أكبر من الحد المسموح." }, 413, origin);
  }
  let payload;
  try { payload = await request.json(); }
  catch { return json({ project: PROJECT, error: "invalid_json",
    message: "تعذّر قراءة طلب المحادثة." }, 400, origin); }

  if (!payload || typeof payload !== "object" || Array.isArray(payload) ||
      payload.api_version !== "1" ||
      typeof payload.message !== "string" ||
      !payload.message.trim() || payload.message.length > 2000 ||
      (payload.history !== undefined && (!Array.isArray(payload.history) ||
        payload.history.length > 8 ||
        !payload.history.every(m => m && ["user", "assistant"].includes(m.role) &&
          typeof m.content === "string" && m.content.length <= 2000)))) {
    return json({ project: PROJECT, error: "invalid_chat_request",
      message: "طلب المحادثة غير صالح." }, 400, origin);
  }

  try {
    const upstream = await fetch(runtimeUrl(env, "/v1/chat"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + env.JON2_RUNTIME_TOKEN,
      },
      body: JSON.stringify({
        contract_version: "1",
        message: payload.message,
        history: (payload.history || []).slice(-8),
        session_id: payload.session_id,
      }),
      signal: AbortSignal.timeout(RUNTIME_TIMEOUT_MS),
    });
    const data = await upstream.json().catch(() => null);
    if (!upstream.ok) {
      return json({ project: PROJECT, error: "runtime_unavailable",
        message: "محرك Jon2 غير متاح حاليًا." },
        upstream.status === 408 || upstream.status === 504 ? 504 : 503, origin);
    }
    if (!data || typeof data.reply !== "string" || !data.reply.trim()) {
      return json({ project: PROJECT, error: "invalid_runtime_response",
        message: "وصل رد غير صالح من محرك Jon2." }, 502, origin);
    }
    return json({
      project: PROJECT,
      api_version: "1",
      request_id: payload.request_id,
      model: data.adapter_loaded ? "Jon2 LoRA on Qwen3.5-4B" : "Qwen3.5-4B preview",
      reply: data.reply.trim(),
      response_mode: data.response_mode,
    }, 200, origin);
  } catch (error) {
    const timedOut = error && (error.name === "TimeoutError" || error.name === "AbortError");
    return json({ project: PROJECT, error: timedOut ? "runtime_timeout" : "runtime_unavailable",
      message: timedOut ? "انتهت مهلة انتظار محرك Jon2." : "محرك Jon2 غير متاح حاليًا." },
      timedOut ? 504 : 503, origin);
  }
}

export default {
  async fetch(request, env = {}) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();
    const origin = request.headers.get("Origin") || "";
    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      return json({ project: PROJECT, error: "origin_not_allowed" }, 403);
    }
    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: {
        ...(origin ? { "Access-Control-Allow-Origin": origin } : {}),
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
      }});
    }
    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return json({ project: PROJECT, status: "alive", service: "edge-gateway" }, 200, origin);
    }
    if (method === "GET" && path === "/api/health") {
      const health = await readRuntimeHealth(env);
      return json({
        project: PROJECT,
        status: "online",
        ...health,
        api_ready: true,
        runtime_api_ready: health.api_ready,
        chat_ready: health.public_chat_ready,
        message: health.public_chat_ready
          ? "محرك Jon2 متصل وجاهز."
          : "البوابة تعمل، لكن المحرك لم يجتز بوابة الإطلاق.",
      }, 200, origin);
    }
    if (method === "POST" && path === "/api/chat") {
      return handleChat(request, origin, env);
    }
    return json({ project: PROJECT, error: "not_found" }, 404, origin);
  },
};
