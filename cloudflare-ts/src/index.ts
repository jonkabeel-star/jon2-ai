import { isChatRequestV1, JON2_API_VERSION, normalizeRuntimeError } from "./contracts";

const PROJECT = "Jon2 Cloud";
const ALLOWED_ORIGINS = new Set([
  "https://jonkabeel-star.github.io",
  "http://localhost:3000",
  "http://127.0.0.1:5500",
]);
const MAX_BODY_BYTES = 64 * 1024;
const RUNTIME_TIMEOUT_MS = 60_000;

interface Env {
  JON2_RUNTIME_URL?: string;
  JON2_RUNTIME_TOKEN?: string;
}

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
  return { project: PROJECT, api_version: JON2_API_VERSION, error, message };
}

function runtimeUrl(env: Env, path: "/v1/health" | "/v1/chat"): URL | null {
  const configured = env.JON2_RUNTIME_URL?.trim();
  if (!configured) return null;
  try {
    const base = new URL(configured);
    if (base.protocol !== "https:" || base.username || base.password) return null;
    return new URL(path, base);
  } catch {
    return null;
  }
}

function runtimeConfigured(env: Env): boolean {
  return Boolean(
    runtimeUrl(env, "/v1/chat") &&
    typeof env.JON2_RUNTIME_TOKEN === "string" &&
    env.JON2_RUNTIME_TOKEN.length >= 32
  );
}

async function runtimeHealth(env: Env): Promise<JsonValue> {
  if (!runtimeConfigured(env)) {
    return {
      api_ready: false,
      model_ready: false,
      model_status: "not_connected",
    };
  }
  try {
    const response = await fetch(runtimeUrl(env, "/v1/health")!, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(8_000),
    });
    const data: unknown = await response.json().catch(() => null);
    if (!response.ok || !data || typeof data !== "object") {
      return { api_ready: false, model_ready: false, model_status: "error" };
    }
    const health = data as Record<string, unknown>;
    const ready = health.model_ready === true;
    return {
      api_ready: health.api_ready === true,
      model_ready: ready,
      model_status: ready ? "ready" : (
        typeof health.model_status === "string" ? health.model_status : "error"
      ),
    };
  } catch {
    return { api_ready: false, model_ready: false, model_status: "error" };
  }
}

function corsPreflight(origin: string): Response {
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return jsonResponse({ project: PROJECT, error: "origin_not_allowed" }, 403);
  }
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": origin || "https://jonkabeel-star.github.io",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    },
  });
}

async function handleChat(request: Request, origin: string, env: Env): Promise<Response> {
  if (!runtimeConfigured(env)) {
    return jsonResponse({
      ...apiError(
        "model_runtime_not_connected",
        "عنوان محرك Python أو مفتاح الاتصال السري غير مضبوط بعد.",
      ),
      chat_ready: false,
    }, 503, origin);
  }

  const contentType = request.headers.get("Content-Type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return jsonResponse(apiError("unsupported_media_type", "أرسل الطلب بصيغة JSON."), 415, origin);
  }

  const contentLength = Number(request.headers.get("Content-Length") ?? "0");
  if (Number.isFinite(contentLength) && contentLength > MAX_BODY_BYTES) {
    return jsonResponse(apiError("request_too_large", "حجم طلب المحادثة أكبر من الحد المسموح."), 413, origin);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse(apiError("invalid_json", "تعذّر قراءة JSON المرسل."), 400, origin);
  }

  if (!isChatRequestV1(payload)) {
    return jsonResponse(
      apiError("invalid_chat_request", "طلب المحادثة غير صالح أو لا يطابق عقد Jon2 API الإصدار 1."),
      400,
      origin,
    );
  }

  try {
    const upstream = await fetch(runtimeUrl(env, "/v1/chat")!, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": `Bearer ${env.JON2_RUNTIME_TOKEN}`,
      },
      body: JSON.stringify({
        contract_version: "1",
        message: payload.message,
        history: (payload.history ?? []).slice(-8),
      }),
      signal: AbortSignal.timeout(RUNTIME_TIMEOUT_MS),
    });

    const data: unknown = await upstream.json().catch(() => null);
    if (!upstream.ok) {
      const normalized = normalizeRuntimeError(upstream.status);
      return jsonResponse({
        ...apiError(normalized.error, normalized.message),
        chat_ready: false,
        request_id: payload.request_id,
      }, upstream.status === 401 || upstream.status === 403 ? 502 : (
        upstream.status === 408 || upstream.status === 504 ? 504 : 503
      ), origin);
    }

    if (!data || typeof data !== "object" ||
        typeof (data as Record<string, unknown>).reply !== "string" ||
        !(data as Record<string, unknown>).reply?.toString().trim()) {
      return jsonResponse(
        apiError("invalid_runtime_response", "وصل رد غير صالح من محرك Jon2."),
        502,
        origin,
      );
    }

    return jsonResponse({
      project: PROJECT,
      api_version: JON2_API_VERSION,
      request_id: payload.request_id,
      model: "Jon2 Original Transformer",
      reply: (data as Record<string, unknown>).reply,
    }, 200, origin);
  } catch (error) {
    const timedOut = error instanceof Error &&
      (error.name === "TimeoutError" || error.name === "AbortError");
    const normalized = normalizeRuntimeError(timedOut ? 504 : 502);
    return jsonResponse(apiError(normalized.error, normalized.message), timedOut ? 504 : 503, origin);
  }
}

export default {
  async fetch(request: Request, env: Env = {}): Promise<Response> {
    const url = new URL(request.url);
    const path = "/" + url.pathname.split("/").filter(Boolean).join("/");
    const method = request.method.toUpperCase();
    const origin = request.headers.get("Origin") ?? "";

    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      return jsonResponse({ project: PROJECT, error: "origin_not_allowed" }, 403);
    }
    if (method === "OPTIONS") return corsPreflight(origin);

    if (method === "GET" && (path === "/" || path === "/api/health/live")) {
      return jsonResponse({
        project: PROJECT,
        status: "alive",
        service: "typescript-edge-api-preview",
      }, 200, origin);
    }

    if (method === "GET" && path === "/api/health") {
      const health = await runtimeHealth(env);
      return jsonResponse({
        project: PROJECT,
        status: "online",
        ...health,
        api_ready: true,
        runtime_api_ready: health.api_ready,
        message: health.model_ready
          ? "محرك Jon2 متصل وجاهز."
          : "البوابة تعمل، لكن محرك Jon2 غير جاهز لتوليد الإجابات.",
      }, 200, origin);
    }

    if (method === "POST" && path === "/api/chat") {
      return handleChat(request, origin, env);
    }
    return jsonResponse({ project: PROJECT, error: "not_found" }, 404, origin);
  },
};
