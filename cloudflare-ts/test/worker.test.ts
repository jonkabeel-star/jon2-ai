import { describe, expect, it } from "vitest";
import worker from "../src/index";

async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const request = new Request(`https://jon2-ai-ts-preview.test${path}`, init);
  return worker.fetch(request, {} as never, {} as never);
}

const validChatRequest = {
  api_version: "1",
  message: "مرحبا",
  history: [{ role: "user", content: "أهلًا" }],
};

describe("Jon2 TypeScript preview Worker", () => {
  it("reports the preview as alive", async () => {
    const response = await call("/api/health/live");
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(200);
    expect(body.status).toBe("alive");
    expect(body.service).toBe("typescript-edge-api-preview");
  });

  it("reports that the real model is not connected", async () => {
    const response = await call("/api/health");
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(200);
    expect(body.api_ready).toBe(true);
    expect(body.model_ready).toBe(false);
    expect(body.model_status).toBe("not_connected");
  });

  it("validates a v1 chat request but never fabricates a response", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validChatRequest),
    });
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(503);
    expect(body.error).toBe("model_runtime_not_connected");
    expect(body.chat_ready).toBe(false);
    expect(body).not.toHaveProperty("reply");
  });

  it("rejects an invalid chat contract before runtime dispatch", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_version: "2", message: "مرحبا" }),
    });
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_chat_request");
    expect(body).not.toHaveProperty("reply");
  });

  it("rejects malformed JSON", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{invalid",
    });
    const body = await response.json() as Record<string, unknown>;

    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_json");
  });

  it("requires JSON content type", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: "مرحبا",
    });
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
    expect(response.headers.get("Access-Control-Allow-Methods"))
      .toContain("POST");
  });
});
