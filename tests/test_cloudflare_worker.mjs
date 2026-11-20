import { readFile } from "node:fs/promises";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { default: worker } = await import(moduleUrl);

const TOKEN = "test-runtime-token-which-is-at-least-32-characters-long";
const ENV = {
  JON2_RUNTIME_URL: "https://private-runtime.example",
  JON2_RUNTIME_TOKEN: TOKEN,
  JON2_PUBLIC_CHAT_ENABLED: "true",
};

async function call(path, init = {}, env = {}) {
  return worker.fetch(new Request(`https://jon2-worker.test${path}`, init), env);
}

describe("Jon2 authenticated Qwen runtime gateway", () => {
  it("reports gateway alive but model disconnected when no runtime is configured", async () => {
    const response = await call("/api/health");
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.api_ready, true);
    assert.equal(body.model_ready, false);
    assert.equal(body.chat_ready, false);
    assert.equal(body.model_status, "not_connected");
  });

  it("refuses public chat when runtime is not configured", async () => {
    const response = await call("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_version: "1", message: "مرحبا" }),
    });
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error, "model_not_released");
  });

  it("keeps public chat closed until inference and human review are complete", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({
      model_ready: true,
      inference_tested: true,
      quality_review_passed: false,
      public_chat_enabled: false,
      model_status: "ready",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
    try {
      const response = await call("/api/health", {}, ENV);
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.model_ready, true);
      assert.equal(body.chat_ready, false);
      assert.equal(body.public_chat_ready, false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("forwards approved chat with the private bearer token and returns the model reply", async () => {
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, init = {}) => {
      calls.push({ url: String(url), init });
      if (String(url).endsWith("/v1/health")) {
        return new Response(JSON.stringify({
          model_ready: true,
          inference_tested: true,
          quality_review_passed: true,
          public_chat_enabled: true,
          model_status: "ready",
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({
        reply: "أهلًا! أنا مساعد Jon2.",
        adapter_loaded: false,
        response_mode: "qwen35_base_preview",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    };
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_version: "1",
          message: "عامل إيه؟",
          history: [{ role: "user", content: "اسمي سامح" }],
        }),
      }, ENV);
      const body = await response.json();
      assert.equal(response.status, 200);
      assert.equal(body.reply, "أهلًا! أنا مساعد Jon2.");
      assert.equal(body.model, "Qwen3.5-4B preview");
      assert.equal(calls.length, 2);
      assert.equal(calls[1].init.headers.Authorization, `Bearer ${TOKEN}`);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("forwards multi-turn history without truncating it at eight messages", async () => {
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, init = {}) => {
      calls.push({ url: String(url), init });
      const payload = String(url).endsWith("/v1/health")
        ? { model_ready: true, inference_tested: true, quality_review_passed: true,
            public_chat_enabled: true, model_status: "ready" }
        : { reply: "فاكر السياق.", adapter_loaded: false,
            response_mode: "qwen35_base_preview" };
      return new Response(JSON.stringify(payload), {
        status: 200, headers: { "Content-Type": "application/json" },
      });
    };
    try {
      const history = Array.from({ length: 12 }, (_, index) => ({
        role: index % 2 === 0 ? "user" : "assistant",
        content: `turn-${index}`,
      }));
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_version: "1", message: "كمل", history }),
      }, ENV);
      assert.equal(response.status, 200);
      const forwarded = JSON.parse(calls[1].init.body);
      assert.equal(forwarded.history.length, 12);
      assert.equal(forwarded.history[0].content, "turn-0");
      assert.equal(forwarded.history[11].content, "turn-11");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("rejects invalid chat payloads after the runtime passes release gates", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({
      model_ready: true,
      inference_tested: true,
      quality_review_passed: true,
      public_chat_enabled: true,
      model_status: "ready",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
    try {
      const response = await call("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_version: "1", message: " " }),
      }, ENV);
      assert.equal(response.status, 400);
      assert.equal((await response.json()).error, "invalid_chat_request");
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
    assert.equal(response.status, 403);
    assert.equal((await response.json()).error, "origin_not_allowed");
  });

  it("allows Authorization during CORS preflight", async () => {
    const response = await call("/api/chat", {
      method: "OPTIONS",
      headers: { Origin: "https://jonkabeel-star.github.io" },
    });
    assert.equal(response.status, 204);
    assert.match(response.headers.get("Access-Control-Allow-Headers"), /Authorization/);
  });
});
