const ALLOWED_ORIGINS = new Set([
  "https://jon2-ai.pages.dev",
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const MAX_MESSAGE_CHARS = 2000;
const WINDOW_MS = 60_000;
const MAX_REQUESTS_PER_WINDOW = 10;
const requestWindows = new Map();

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

function isRateLimited(request) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const now = Date.now();
  const current = requestWindows.get(ip);
  if (!current || now - current.start >= WINDOW_MS) {
    requestWindows.set(ip, { start: now, count: 1 });
    if (requestWindows.size > 2000) {
      for (const [key, value] of requestWindows) {
        if (now - value.start >= WINDOW_MS) requestWindows.delete(key);
      }
    }
    return false;
  }
  current.count += 1;
  return current.count > MAX_REQUESTS_PER_WINDOW;
}

function coreUrl(env, path) {
  if (!env.JON2_CORE_URL) return null;
  try {
    const base = new URL(env.JON2_CORE_URL);
    if (base.protocol !== "https:" || base.username || base.password ||
        base.search || base.hash || base.pathname !== "/") return null;
    return new URL(path, base).toString();
  } catch {
    return null;
  }
}

async function readCoreHealth(env) {
  const target = coreUrl(env, "/api/health");
  if (!target) return null;
  const response = await fetch(target, {
    headers: { "Accept": "application/json" },
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) return null;
  return await response.json();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();
    const origin = allowedOrigin(request);

    if (origin === null) {
      return json({ project: "Jon2 Independent Core", error: "origin_not_allowed" }, 403);
    }

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
      return json({
        project: "Jon2 Independent Core Gateway",
        status: "alive",
        service: "gateway_only",
        external_ai_provider: false,
      }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      try {
        const core = await readCoreHealth(env);
        return json({
          project: "Jon2 Independent Core",
          status: "online",
          api_ready: true,
          gateway_ready: true,
          external_ai_provider: false,
          runtime_api_ready: Boolean(core),
          model_ready: core?.model_loaded === true,
          chat_ready: core?.chat_ready === true,
          model_status: core
            ? (core.chat_ready ? "independent_core_ready" : "independent_core_release_blocked")
            : "independent_core_not_configured",
          message: core
            ? (core.chat_ready
              ? "خادم Jon2 الأصلي متصل."
              : "خادم Jon2 الأصلي متصل، لكن المحادثة ما زالت مغلقة حتى اجتياز اختبارات الجودة والموافقة.")
            : "تم فصل مزود الذكاء الاصطناعي الخارجي. خادم Jon2 المستقل لم يتم ربطه بعد.",
        }, 200, origin);
      } catch {
        return json({
          project: "Jon2 Independent Core",
          status: "online",
          api_ready: true,
          gateway_ready: true,
          runtime_api_ready: false,
          model_ready: false,
          chat_ready: false,
          external_ai_provider: false,
          message: "بوابة Jon2 تعمل، لكن تعذر الوصول إلى خادم Jon2 المستقل.",
        }, 200, origin);
      }
    }

    if (method === "POST" && path === "/api/chat") {
      if (isRateLimited(request)) {
        return json({
          project: "Jon2 Independent Core",
          error: "rate_limited",
          message: "طلبات كثيرة خلال دقيقة واحدة. انتظر قليلًا ثم حاول مجددًا.",
        }, 429, origin);
      }

      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "invalid_json", message: "تعذر قراءة الرسالة." }, 400, origin);
      }

      const message = typeof body?.message === "string" ? body.message.trim() : "";
      const sessionId = typeof body?.session_id === "string" ? body.session_id : "";
      const validSessionId = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/.test(sessionId);
      if (!message || message.length > MAX_MESSAGE_CHARS || !validSessionId) {
        return json({
          error: "invalid_request",
          message: "الرسالة أو معرّف المحادثة غير صالح.",
        }, 400, origin);
      }

      const target = coreUrl(env, "/api/chat");
      if (!target) {
        return json({
          project: "Jon2 Independent Core",
          error: "independent_core_not_configured",
          chat_ready: false,
          message: "تم فصل مزود الذكاء الاصطناعي الخارجي. محرك Jon2 الأصلي لم يتم تشغيله على خادمه بعد.",
        }, 503, origin);
      }

      try {
        const response = await fetch(target, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId }),
          signal: AbortSignal.timeout(60_000),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = typeof payload.detail === "string"
            ? payload.detail
            : typeof payload.message === "string"
              ? payload.message
              : "خادم Jon2 المستقل غير جاهز حاليًا.";
          return json({
            project: "Jon2 Independent Core",
            error: "independent_core_not_ready",
            chat_ready: false,
            message: detail,
          }, response.status >= 500 ? 503 : response.status, origin);
        }
        if (typeof payload.reply !== "string" || !payload.reply.trim()) {
          return json({
            project: "Jon2 Independent Core",
            error: "empty_core_response",
            message: "خادم Jon2 لم يُرجع إجابة نصية.",
          }, 502, origin);
        }
        return json({
          project: "Jon2 Independent Core",
          reply: payload.reply.trim(),
          chat_ready: true,
          response_mode: "original_jon2_model",
        }, 200, origin);
      } catch {
        return json({
          project: "Jon2 Independent Core",
          error: "independent_core_unreachable",
          chat_ready: false,
          message: "تعذر الاتصال بخادم Jon2 الأصلي. حاول لاحقًا.",
        }, 502, origin);
      }
    }

    return json({ project: "Jon2 Independent Core", error: "not_found" }, 404, origin);
  },
};
