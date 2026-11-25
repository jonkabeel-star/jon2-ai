import { readFile } from "node:fs/promises";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { default: worker } = await import(moduleUrl);

async function call(path, init = {}, env = {}) {
  return worker.fetch(new Request(`https://jon2-worker.test${path}`, init), env);
}

describe("Jon2 Cloudflare private runtime bridge", () => {
  it("reports edge liveness without claiming a configured model runtime", async () => {
    const response = await call("/api/health/live");
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.status, "alive");
    assert.equal(body.model_runtime, "not_configured");
  });

  it("reports model unavailable while no private runtime is configured", async () => {
    const response = await call("/api/health");
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.api_ready, true);
    assert.equal(body.model_ready, false);
    assert.equal(body.chat_ready, false);
    assert.equal(body.model_status, "runtime_not_configured");
  });

  it("refuses chat without contacting a remote runtime when config is absent", async () => {
    const originalFetch = globalThis.fetch;
    let networkCalls = 0;
    globalThis.fetch = async () => {
      networkCalls += 1;
      throw new Error("Network must not be used");
    };
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "مرحبا" }),
      });
      const body = await response.json();
      assert.equal(response.status, 503);
      assert.equal(body.error, "runtime_not_configured");
      assert.equal(body.chat_ready, false);
      assert.equal(networkCalls, 0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("forwards a valid chat request with the private token held server-side", async () => {
    const originalFetch = globalThis.fetch;
    let captured;
    globalThis.fetch = async (url, options) => {
      captured = { url: String(url), options };
      return new Response(JSON.stringify({
        contract_version: "1",
        project: "Jon2 AI",
        reply: "أهلًا بك",
        session_id: null,
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "مرحبا", history: [] }),
      }, {
        JON2_RUNTIME_URL: "https://private-runtime.example",
        JON2_RUNTIME_TOKEN: "x".repeat(40),
      });
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.reply, "أهلًا بك");
      assert.equal(captured.url, "https://private-runtime.example/v1/chat");
      assert.equal(captured.options.headers.Authorization, `Bearer ${"x".repeat(40)}`);
      assert.deepEqual(JSON.parse(captured.options.body), {
        contract_version: "1",
        message: "مرحبا",
        history: [],
      });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects non-HTTPS runtime URLs without making a network request", async () => {
    const originalFetch = globalThis.fetch;
    let networkCalls = 0;
    globalThis.fetch = async () => {
      networkCalls += 1;
      throw new Error("Network must not be used");
    };
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "مرحبا" }),
      }, {
        JON2_RUNTIME_URL: "http://private-runtime.example",
        JON2_RUNTIME_TOKEN: "x".repeat(40),
      });
      assert.equal(response.status, 503);
      assert.equal(networkCalls, 0);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("allows the published GitHub Pages origin", async () => {
    const response = await call("/api/health", {
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
