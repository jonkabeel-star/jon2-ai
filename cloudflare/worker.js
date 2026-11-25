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
  const rawUrl = (env.JON2_RUNTIME_URL || "").trim();
  const token = (env.JON2_RUNTIME_TOKEN || "").trim();
  if (!rawUrl || token.length < 32) return null;

  try {
    const url = new URL(rawUrl);
    if (url.protocol !== "https:" || url.username || url.password) return null;
    url.pathname = url.pathname.replace(/\/+$/, "");
    url.search = "";
    url.hash = "";
    return { baseUrl: url.toString().replace(/\/$/, ""), token };
  } catch {
    return null;
  }
}

async function callRuntime(env, path, payload = undefined) {
  const config = runtimeConfig(env);
  if (!config) {
    return {
      configured: false,
      response: null,
    };
  }

  const headers = {
    "Authorization": `Bearer ${config.token}`,
    "Accept": "application/json",
  };
  const options = {
    method: payload === undefined ? "GET" : "POST",
    headers,
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(20000),
  };
  if (payload !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }

  try {
    const response = await fetch(`${config.baseUrl}${path}`, options);
    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      return {
        configured: true,
        response: json({
          project: "Jon2 Cloud",
          error: "runtime_invalid_response",
          message: "خادم Jon2 أرسل استجابة غير صالحة.",
        }, 502),
      };
    }
    return { configured: true, upstreamStatus: response.status, data };
  } catch (error) {
    const timedOut = error?.name === "TimeoutError" || error?.name === "AbortError";
    return {
      configured: true,
      response: json({
        project: "Jon2 Cloud",
        error: timedOut ? "runtime_timeout" : "runtime_unavailable",
        message: timedOut
          ? "انتهت مهلة انتظار محرك Jon2."
          : "تعذر الاتصال بخادم محرك Jon2.",
      }, timedOut ? 504 : 502),
    };
  }
}

function validChatRequest(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return false;
  if (typeof body.message !== "string" || !body.message.trim() || body.message.length > 2000) return false;
  if (body.history !== undefined) {
    if (!Array.isArray(body.history) || body.history.length > 8) return false;
    for (const item of body.history) {
      if (!item || typeof item !== "object" || Array.isArray(item)) return false;
      if (!["user", "assistant"].includes(item.role)) return false;
      if (typeof item.content !== "string" || !item.content.trim() || item.content.length > 2000) return false;
    }
  }
  if (body.session_id !== undefined && body.session_id !== null) {
    if (typeof body.session_id !== "string" ||
        !/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/.test(body.session_id)) {
      return false;
    }
  }
  return true;
}

export default {
  async fetch(request, env = {}) {
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
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
          "Vary": "Origin",
        },
      });
    }

    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return json({
        project: "Jon2 Cloud",
        status: "alive",
        service: "edge-gateway",
        model_runtime: runtimeConfig(env) ? "configured" : "not_configured",
      }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      const result = await callRuntime(env, "/v1/health");
      if (!result.configured) {
        return json({
          project: "Jon2 Cloud",
          status: "online",
          api_ready: true,
          model_ready: false,
          chat_ready: false,
          inference_tested: false,
          model_status: "runtime_not_configured",
          model: "Jon2 Original Transformer",
          model_type: "project_owned_checkpoint_required",
          message: "لم يتم توصيل خادم تشغيل عقل Jon2 بعد.",
        }, 200, origin);
      }
      if (result.response) return json(await result.response.json(), result.response.status, origin);
      return json({
        project: "Jon2 Cloud",
        ...result.data,
      }, result.upstreamStatus, origin);
    }

    if (method === "POST" && path === "/api/chat") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ project: "Jon2 Cloud", error: "invalid_json" }, 400, origin);
      }
      if (!validChatRequest(body)) {
        return json({
          project: "Jon2 Cloud",
          error: "invalid_request",
          message: "بيانات الرسالة غير صالحة.",
        }, 400, origin);
      }

      const result = await callRuntime(env, "/v1/chat", {
        contract_version: "1",
        message: body.message,
        history: body.history || [],
        ...(body.session_id ? { session_id: body.session_id } : {}),
      });
      if (!result.configured) {
        return json({
          project: "Jon2 Cloud",
          error: "runtime_not_configured",
          chat_ready: false,
          message: "عقل Jon2 غير متصل بخادم التشغيل بعد.",
        }, 503, origin);
      }
      if (result.response) return json(await result.response.json(), result.response.status, origin);
      return json(result.data, result.upstreamStatus, origin);
    }

    return json({ project: "Jon2 Cloud", error: "not_found" }, 404, origin);
  },
};
