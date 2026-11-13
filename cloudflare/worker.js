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

export default {
  async fetch(request) {
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
        message: "بوابة Jon2 تعمل، لكن خادم النموذج الأصلي وملف أوزانه لم يُربطا بعد. المحادثة متوقفة بدل استخدام نموذج خارجي.",
      }, 200, origin);
    }

    if (method === "POST" && path === "/api/chat") {
      // Fail closed: never call Cloudflare Workers AI or another hosted model.
      // The original Jon2 checkpoint must be served by the approved private runtime.
      return json({
        project: "Jon2 Cloud",
        error: "model_runtime_not_connected",
        chat_ready: false,
        message: "لم يتم ربط محرك Jon2 الأصلي بعد. لن نستخدم نموذجًا خارجيًا أو نولّد ردودًا وهمية.",
      }, 503, origin);
    }

    return json({ project: "Jon2 Cloud", error: "not_found" }, 404, origin);
  },
};
