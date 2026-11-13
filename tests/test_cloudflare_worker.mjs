import { readFile } from "node:fs/promises";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const { default: worker } = await import(moduleUrl);

async function call(path, init = {}) {
  return worker.fetch(new Request(`https://jon2-worker.test${path}`, init));
}

describe("local-only Jon2 edge gateway", () => {
  it("reports gateway liveness without claiming model readiness", async () => {
    const response = await call("/api/health");
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.api_ready, true);
    assert.equal(body.model_ready, false);
    assert.equal(body.chat_ready, false);
    assert.equal(body.model_status, "original_model_runtime_not_connected");
  });

  it("refuses chat without contacting any remote runtime", async () => {
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
      assert.equal(body.error, "local_model_not_loaded");
      assert.equal(body.chat_ready, false);
      assert.equal(body.message, "عقل Jon2 غير جاهز للرد");
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
