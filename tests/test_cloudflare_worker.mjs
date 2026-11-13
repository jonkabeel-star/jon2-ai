import { readFile } from "node:fs/promises";
import { after, describe, it } from "node:test";
import assert from "node:assert/strict";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { default: worker } = await import(moduleUrl);

async function call(path, init = {}, env = {}) {
  return worker.fetch(
    new Request(`https://jon2-worker.test${path}`, init),
    env,
  );
}

describe("production Cloudflare gateway uses original Jon2 only", () => {
  it("reports a live gateway but keeps health unavailable until Python is configured", async () => {
    const response = await call("/api/health");
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.api_ready, true);
    assert.equal(body.gateway_ready, true);
    assert.equal(body.runtime_configured, false);
    assert.equal(body.model_ready, false);
    assert.equal(body.chat_ready, false);
    assert.equal(body.model_status, "runtime_configuration_missing");
  });

  it("fails chat closed and never calls a hosted AI binding", async () => {
    let calls = 0;
    const env = { AI: { run: async () => { calls += 1; return { response: "not allowed" }; } } };
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "مرحبا" }),
    }, env);
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.error, "runtime_not_configured");
    assert.equal(body.chat_ready, false);
    assert.equal(calls, 0);
  });

  it("proxies health to the authenticated private Python runtime", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      assert.equal(String(input), "https://python-runtime.example/v1/health");
      return new Response(JSON.stringify({
        api_ready: true,
        model_ready: true,
        chat_ready: true,
        inference_tested: true,
        quality_review_passed: true,
        model_status: "ready",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    try {
      const response = await call("/api/health", {}, {
        JON2_RUNTIME_URL: "https://python-runtime.example",
        JON2_RUNTIME_TOKEN: "r".repeat(48),
      });
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.runtime_configured, true);
      assert.equal(body.model_ready, true);
      assert.equal(body.chat_ready, true);
      assert.equal(body.model_type, "jon2_original");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("forwards chat only to the private Jon2 runtime with its server-side token", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input, init) => {
      assert.equal(String(input), "https://python-runtime.example/v1/chat");
      assert.equal(new Headers(init.headers).get("Authorization"), "Bearer " + "s".repeat(48));
      const sent = JSON.parse(init.body);
      assert.equal(sent.contract_version, "1");
      assert.equal(sent.message, "مرحبا");
      assert.equal(sent.history.length, 1);
      return new Response(JSON.stringify({
        reply: "أهلًا بك.",
        session_id: sent.session_id,
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "مرحبا",
          history: [{ role: "user", content: "سابق" }],
        }),
      }, {
        JON2_RUNTIME_URL: "https://python-runtime.example",
        JON2_RUNTIME_TOKEN: "s".repeat(48),
      });
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.reply, "أهلًا بك.");
      assert.equal(body.response_mode, "original_jon2_runtime");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("allows the published GitHub Pages origin", async () => {
    const response = await call("/api/health/live", {
      headers: { Origin: "https://jonkabeel-star.github.io" },
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), "https://jonkabeel-star.github.io");
  });

  it("rejects unapproved browser origins", async () => {
    const response = await call("/api/health", {
      headers: { Origin: "https://untrusted.example" },
    });
    const body = await response.json();
    assert.equal(response.status, 403);
    assert.equal(body.error, "origin_not_allowed");
  });

  it("supports CORS preflight", async () => {
    const response = await call("/api/chat", {
      method: "OPTIONS",
      headers: { Origin: "https://jonkabeel-star.github.io" },
    });
    assert.equal(response.status, 204);
    assert.equal(response.headers.get("Access-Control-Allow-Methods"), "GET, POST, OPTIONS");
  });
});
