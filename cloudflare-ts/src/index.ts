import { isChatRequestV1, JON2_API_VERSION } from "./contracts";

const PROJECT = "Jon2 Cloud";
const ALLOWED_ORIGINS = new Set([
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const MAX_BODY_BYTES = 512 * 1024;

type JsonValue = Record<string, unknown>;

function jsonResponse(
  payload: JsonValue,
  status = 200,
  requestOrigin = "",
): Response {
  const headers = new Headers({
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Vary": "Origin",
  });

  if (requestOrigin && ALLOWED_ORIGINS.has(requestOrigin)) {
    headers.set("Access-Control-Allow-Origin", requestOrigin);
  }

  return new Response(JSON.stringify(payload), { status, headers });
}

function apiError(error: string, message: string): JsonValue {
  return {
    project: PROJECT,
    api_version: JON2_API_VERSION,
    error,
    message,
  };
}

function corsPreflight(origin: string): Response {
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return jsonResponse({ project: PROJECT, error: "origin_not_allowed" }, 403);
  }

  const headers = new Headers({
    "Access-Control-Allow-Origin": origin || "https://jonkabeel-star.github.io",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  });

  return new Response(null, { status: 204, headers });
}

async function handleChat(request: Request, origin: string): Promise<Response> {
  const contentType = request.headers.get("Content-Type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return jsonResponse(
      apiError("unsupported_media_type", "أرسل الطلب بصيغة JSON."),
      415,
      origin,
    );
  }

  const contentLength = Number(request.headers.get("Content-Length") ?? "0");
  if (Number.isFinite(contentLength) && contentLength > MAX_BODY_BYTES) {
    return jsonResponse(
      apiError("request_too_large", "حجم طلب المحادثة أكبر من الحد المسموح."),
      413,
      origin,
    );
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse(
      apiError("invalid_json", "تعذّر قراءة JSON المرسل."),
      400,
      origin,
    );
  }

  if (!isChatRequestV1(payload)) {
    return jsonResponse(
      apiError(
        "invalid_chat_request",
        "طلب المحادثة غير صالح أو لا يطابق عقد Jon2 API الإصدار 1.",
      ),
      400,
      origin,
    );
  }

  // Intentionally no upstream call: a real, approved model runtime is not connected.
  return jsonResponse({
    ...apiError(
      "model_runtime_not_connected",
      "لم يتم ربط محرك Jon2 الحقيقي بعد. لن نولّد ردودًا وهمية.",
    ),
    chat_ready: false,
    request_id: payload.request_id,
  }, 503, origin);
}

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\\/+$/, "") || "/";
    const method = request.method.toUpperCase();
    const origin = request.headers.get("Origin") ?? "";

    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      return jsonResponse({ project: PROJECT, error: "origin_not_allowed" }, 403);
    }

    if (method === "OPTIONS") {
      return corsPreflight(origin);
    }

    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return jsonResponse({
        project: PROJECT,
        status: "alive",
        service: "typescript-edge-api-preview",
        model_runtime: "not_connected",
      }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      return jsonResponse({
        project: PROJECT,
        status: "online",
        api_ready: true,
        model_ready: false,
        model_status: "not_connected",
        message: "واجهة Jon2 تعمل، لكن محرك النموذج الحقيقي غير مربوط بعد.",
      }, 200, origin);
    }

    if (method === "POST" && path === "/api/chat") {
      return handleChat(request, origin);
    }

    return jsonResponse({ project: PROJECT, error: "not_found" }, 404, origin);
  },
};
