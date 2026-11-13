import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { default: worker } = await import(moduleUrl);
const ORIGIN = "https://jonkabeel-star.github.io";
const ENV = { JON2_RUNTIME_URL: "https://jon2-api.example.com", JON2_RUNTIME_TOKEN: "x".repeat(48) };

async function call(path, init = {}, env = {}) {
  return worker.fetch(new Request(`https://jon2-worker.test${path}`, init), env);
}

describe("Cloudflare gateway proxies only to the private original Jon2 runtime", () => {
  it("reports the edge online but the private runtime not configured", async () => {
    const response = await call("/api/health");
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.api_ready, true);
    assert.equal(body.model_ready, false);
    assert.equal(body.chat_ready, false);
    assert.equal(body.model_status, "runtime_not_configured");
  });

  it("fails chat closed when runtime secrets are absent", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "مرحبا" }),
    }, { AI: { run: async () => { throw new Error("external AI must never run"); } } });
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.error, "model_runtime_not_connected");
    assert.equal(body.chat_ready, false);
  });

  it("rejects non-HTTPS runtime URLs and short tokens", async () => {
    const response = await call("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "مرحبا" }),
    }, { JON2_RUNTIME_URL: "http://unsafe.example", JON2_RUNTIME_TOKEN: "short" });
    assert.equal(response.status, 503);
  });

  it("proxies authenticated health and keeps the quality gate closed", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (url, init = {}) => {
        assert.equal(String(url), "https://jon2-api.example.com/v1/health");
        assert.equal(init.method, undefined);
        return new Response(JSON.stringify({
          api_ready: true, model_ready: false, model_status: "human_quality_review_pending",
          inference_tested: true, quality_review_passed: false,
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      };
      const response = await call("/api/health", { headers: { Origin: ORIGIN } }, ENV);
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.runtime_api_ready, true);
      assert.equal(body.model_ready, false);
      assert.equal(body.chat_ready, false);
      assert.equal(body.model_status, "human_quality_review_pending");
      assert.equal(response.headers.get("Access-Control-Allow-Origin"), ORIGIN);
    } finally { globalThis.fetch = originalFetch; }
  });

  it("forwards chat only to the authenticated Jon2 /v1/chat endpoint", async () => {
    const originalFetch = globalThis.fetch;
    try {
      globalThis.fetch = async (url, init = {}) => {
        assert.equal(String(url), "https://jon2-api.example.com/v1/chat");
        assert.equal(init.headers.Authorization, "Bearer " + ENV.JON2_RUNTIME_TOKEN);
        const payload = JSON.parse(init.body);
        assert.equal(payload.contract_version, "1");
        assert.equal(payload.message, "مرحبا");
        return new Response(JSON.stringify({ reply: "رد تجريبي من محرك Jon2", session_id: "session-1" }), {
          status: 200, headers: { "Content-Type": "application/json" },
        });
      };
      const response = await call("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json", Origin: ORIGIN },
        body: JSON.stringify({ message: "مرحبا" }),
      }, ENV);
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.model, "Jon2 Original Transformer");
      assert.equal(body.reply, "رد تجريبي من محرك Jon2");
    } finally { globalThis.fetch = originalFetch; }
  });

  it("rejects malformed requests and unapproved browser origins", async () => {
    const invalid = await call("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "" }),
    }, ENV);
    assert.equal(invalid.status, 400);
    const denied = await call("/api/health", { headers: { Origin: "https://untrusted.example" } }, ENV);
    assert.equal(denied.status, 403);
  });

  it("supports CORS preflight with Authorization", async () => {
    const response = await call("/api/chat", { method: "OPTIONS", headers: { Origin: ORIGIN } });
    assert.equal(response.status, 204);
    assert.match(response.headers.get("Access-Control-Allow-Headers"), /Authorization/);
  });
});
