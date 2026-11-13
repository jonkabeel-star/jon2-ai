const ALLOWED_ORIGINS = new Set([
  "https://jon2-ai.pages.dev",
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);

function json(payload, status = 200, origin = "") {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
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

function runtimeConfig(env) {
  const rawUrl = typeof env.JON2_RUNTIME_URL === "string" ? env.JON2_RUNTIME_URL.trim() : "";
  const token = typeof env.JON2_RUNTIME_TOKEN === "string" ? env.JON2_RUNTIME_TOKEN.trim() : "";
  if (!rawUrl || token.length < 32) return null;
  try {
    const url = new URL(rawUrl);
    if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) return null;
    url.pathname = url.pathname.replace(/\/+$/, "");
    return { base: url.toString().replace(/\/$/, ""), token };
  } catch {
    return null;
  }
}

async function runtimeFetch(config, path, init = {}) {
  return fetch(config.base + path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
    signal: AbortSignal.timeout(25000),
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();
    const origin = allowedOrigin(request);

    if (origin === null) return json({ project: "Jon2 Cloud", error: "origin_not_allowed" }, 403);

    if (method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          ...(origin ? { "Access-Control-Allow-Origin": origin } : {}),
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
          "Vary": "Origin",
        },
      });
    }

    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return json({ project: "Jon2 Cloud", status: "alive", service: "edge-gateway" }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      const config = runtimeConfig(env);
      if (!config) {
        return json({
          project: "Jon2 Cloud",
          status: "online",
          api_ready: true,
          gateway_ready: true,
          runtime_configured: false,
          model_ready: false,
          chat_ready: false,
          inference_tested: false,
          model_status: "runtime_configuration_missing",
          message: "بوابة Jon2 تعمل. يلزم ربط عنوان خادم Python وسر المصادقة الخاص به.",
        }, 503, origin);
      }
      try {
        const upstream = await runtimeFetch(config, "/v1/health");
        const health = await upstream.json().catch(() => ({}));
        if (!upstream.ok || health.api_ready !== true) {
          return json({
            project: "Jon2 Cloud",
            status: "online",
            gateway_ready: true,
            runtime_configured: true,
            runtime_auth_ready: health.api_ready === true,
            model_ready: false,
            chat_ready: false,
            model_status: upstream.ok ? "python_runtime_auth_not_configured" : "python_runtime_health_failed",
          }, 503, origin);
        }
        const modelReady = Boolean(health.model_ready);
        const chatReady = Boolean(health.chat_ready);
        return json({
          project: "Jon2 Cloud",
          status: "online",
          api_ready: true,
          gateway_ready: true,
          runtime_configured: true,
          model_ready: modelReady,
          chat_ready: chatReady,
          inference_tested: Boolean(health.inference_tested),
          quality_review_passed: Boolean(health.quality_review_passed),
          model_status: String(health.model_status || "unknown"),
          model_type: "jon2_original",
          message: chatReady
            ? "اتصلت بوابة Jon2 بخادم النموذج الأصلي."
            : "خادم Python متصل، لكن النموذج لم يجتز شروط جاهزية المحادثة بعد.",
        }, chatReady ? 200 : 503, origin);
      } catch {
        return json({
          project: "Jon2 Cloud",
          status: "online",
          gateway_ready: true,
          runtime_configured: true,
          model_ready: false,
          chat_ready: false,
          model_status: "python_runtime_unreachable",
          message: "تعذر الوصول إلى خادم Python. تحقق من عنوان الخدمة وحالتها.",
        }, 503, origin);
      }
    }

    if (method === "POST" && path === "/api/chat") {
      const config = runtimeConfig(env);
      if (!config) {
        return json({
          project: "Jon2 Cloud",
          error: "runtime_not_configured",
          chat_ready: false,
          message: "خادم Jon2 Python غير مربوط بعد.",
        }, 503, origin);
      }
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ project: "Jon2 Cloud", error: "invalid_json" }, 400, origin);
      }
      if (!body || typeof body.message !== "string" || !body.message.trim() || body.message.length > 2000) {
        return json({ project: "Jon2 Cloud", error: "invalid_message" }, 400, origin);
      }
      const history = Array.isArray(body.history)
        ? body.history.slice(-8).filter(item =>
            item && (item.role === "user" || item.role === "assistant") &&
            typeof item.content === "string" && item.content.trim()
          ).map(item => ({ role: item.role, content: item.content.slice(0, 2000) }))
        : [];
      const payload = {
        contract_version: "1",
        message: body.message.trim(),
        history,
      };
      if (typeof body.session_id === "string" &&
          /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(body.session_id)) {
        payload.session_id = body.session_id;
      }
      try {
        const upstream = await runtimeFetch(config, "/v1/chat", {
          method: "POST",
          headers: { Authorization: "Bearer " + config.token },
          body: JSON.stringify(payload),
        });
        const result = await upstream.json().catch(() => ({}));
        if (!upstream.ok) {
          const unavailable = upstream.status === 503;
          return json({
            project: "Jon2 Cloud",
            error: result.error || (unavailable ? "model_not_ready" : "runtime_request_failed"),
            chat_ready: false,
            message: result.detail || "لم يتمكن محرك Jon2 الأصلي من إكمال الطلب.",
          }, upstream.status >= 400 && upstream.status < 600 ? upstream.status : 502, origin);
        }
        if (typeof result.reply !== "string" || !result.reply.trim()) {
          return json({ project: "Jon2 Cloud", error: "empty_model_reply", chat_ready: false }, 502, origin);
        }
        return json({
          project: "Jon2 AI",
          reply: result.reply.trim(),
          session_id: result.session_id || payload.session_id || null,
          response_mode: "original_jon2_runtime",
        }, 200, origin);
      } catch {
        return json({
          project: "Jon2 Cloud",
          error: "python_runtime_unreachable",
          chat_ready: false,
          message: "تعذر الاتصال بخادم Python. لم يتم استخدام نموذج بديل.",
        }, 502, origin);
      }
    }

    return json({ project: "Jon2 Cloud", error: "not_found" }, 404, origin);
  },
};
