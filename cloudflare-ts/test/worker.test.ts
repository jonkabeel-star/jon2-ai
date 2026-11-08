import { afterEach, describe, expect, it, vi } from "vitest";
import worker from "../src/index";

async function call(
  path: string,
  init: RequestInit = {},
  env: Record<string, string> = {},
): Promise<Response> {
  const request = new Request(`https://jon2-ai-ts-preview.test${path}`, init);
  return worker.fetch(request, env as never, {} as never);
}

const validChatRequest = {
  api_version: "1",
  message: "مرحبا",
  history: [{ role: "user", content: "أهلًا" }],
  session_id: "123e4567-e89b-42d3-a456-426614174000",
};
const runtimeEnv = {
  JON2_RUNTIME_URL: "https://python-runtime.example/",
  JON2_RUNTIME_TOKEN: "x".repeat(48),
};

afterEach(() => vi.unstubAllGlobals());

describe("Jon2 TypeScript preview Worker", () => {
  it("reports the preview as alive", async () => {
    const response = await call("/api/health/live");
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(200);
    expect(body.status).toBe("alive");
  });

  it("reports no runtime when private settings are absent", async () => {
    const response = await call("/api/health");
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(200);
    expect(body.api_ready).toBe(true);
    expect(body.model_ready).toBe(false);
    expect(body.model_status).toBe("not_connected");
  });

  it("proxies a valid Arabic request to the authenticated Python runtime", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("https://python-runtime.example/v1/chat");
      expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${runtimeEnv.JON2_RUNTIME_TOKEN}`);
      const body = JSON.parse(String(init?.body));
      expect(body.contract_version).toBe("1");
      expect(body.message).toBe("مرحبا");
      expect(body.history).toEqual(validChatRequest.history);
      expect(body.session_id).toBe(validChatRequest.session_id);
      return new Response(JSON.stringify({ reply: "أهلًا بك." }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...validChatRequest, request_id: "req-1" }),
    }, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(200);
    expect(body.reply).toBe("أهلًا بك.");
    expect(body.request_id).toBe("req-1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not call a runtime when its URL or secret is missing", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validChatRequest),
    });
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(503);
    expect(body.error).toBe("model_runtime_not_connected");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reports model readiness from the Python runtime health endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      api_ready: true,
      model_ready: true,
      model_status: "ready",
    }), { status: 200 })));
    const response = await call("/api/health", {}, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;
    expect(body.model_ready).toBe(true);
    expect(body.model_status).toBe("ready");
  });

  it("normalizes an upstream authorization failure without exposing details", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: "private token detail" }),
      { status: 401 },
    )));
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validChatRequest),
    }, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(502);
    expect(body.error).toBe("runtime_unauthorized");
    expect(JSON.stringify(body)).not.toContain("private token detail");
  });

  it("rejects invalid chat contracts before runtime dispatch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_version: "2", message: "مرحبا" }),
    }, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_chat_request");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects malformed JSON", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{invalid",
    }, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_json");
  });

  it("requires JSON content type", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: "مرحبا",
    }, runtimeEnv);
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(415);
    expect(body.error).toBe("unsupported_media_type");
  });

  it("rejects unknown routes", async () => {
    const response = await call("/not-a-route");
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(404);
    expect(body.error).toBe("not_found");
  });

  it("rejects unapproved browser origins", async () => {
    const response = await call("/api/health", {
      headers: { Origin: "https://untrusted.example" },
    });
    const body = await response.json() as Record<string, unknown>;
    expect(response.status).toBe(403);
    expect(body.error).toBe("origin_not_allowed");
  });

  it("supports preflight from the GitHub Pages site", async () => {
    const response = await call("/api/chat", {
      method: "OPTIONS",
      headers: { Origin: "https://jonkabeel-star.github.io" },
    });
    expect(response.status).toBe(204);
    expect(response.headers.get("Access-Control-Allow-Origin"))
      .toBe("https://jonkabeel-star.github.io");
    expect(response.headers.get("Access-Control-Allow-Methods")).toContain("POST");
  });
});
