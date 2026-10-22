const http = require("http");
const crypto = require("crypto");
const PORT = process.env.PORT || 3000;
const apiKeys = new Map();
function send(res, status, data) {
  res.writeHead(status);
  res.end(JSON.stringify(data));
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk;
      if (body.length > 100000) {
        reject(new Error("Request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        reject(new Error("Invalid JSON"));
      }
    });
    req.on("error", reject);
  });
}
const server = http.createServer(async (req, res) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization"
  );
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  if (url.pathname === "/api/health" && req.method === "GET") {
    return send(res, 200, {
      project: "Jon2 AI",
      status: "online",
      aiEngine: "not_connected",
      chatEndpoint: "/api/chat"
    });
  }
  // واجهة المحادثة
  if (url.pathname === "/api/chat" && req.method === "POST") {
    let body;
    try {
      body = await readBody(req);
    } catch (error) {
      return send(res, 400, { error: error.message });
    }
    if (typeof body.message !== "string" || !body.message.trim()) {
      return send(res, 400, {
        error: "Please provide a message."
      });
    }
    // لا نُرجع إجابة وهمية قبل ربط نموذج فعلي.
    return send(res, 503, {
      project: "Jon2 AI",
      error: "AI_MODEL_NOT_CONNECTED",
      message:
        "Jon2 AI chat endpoint is ready, but the language model has not been connected yet."
    });
  }
  if (url.pathname === "/api/keys" && req.method === "POST") {
    let body;
    try {
      body = await readBody(req);
    } catch (error) {
      return send(res, 400, { error: error.message });
    }
    const adminSecret = process.env.JON2_ADMIN_SECRET;
    if (!adminSecret || body.adminSecret !== adminSecret) {
      return send(res, 403, {
        error: "Not authorized to create API keys"
      });
    }
    const key = "jon2_sk_" + crypto.randomBytes(32).toString("hex");
    const hash = crypto.createHash("sha256").update(key).digest("hex");
    apiKeys.set(hash, {
      createdAt: new Date().toISOString()
    });
    return send(res, 201, {
      project: "Jon2 AI",
      apiKey: key,
      warning: "Save this key securely. It will not be shown again."
    });
  }
  if (url.pathname === "/api/keys/verify" && req.method === "POST") {
    const auth = req.headers.authorization || "";
    const key = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    if (!key.startsWith("jon2_sk_")) {
      return send(res, 401, {
        valid: false,
        error: "Missing or invalid API key"
      });
    }
    const hash = crypto.createHash("sha256").update(key).digest("hex");
    const valid = apiKeys.has(hash);
    return send(res, valid ? 200 : 401, { valid });
  }
  return send(res, 404, {
    error: "Endpoint not found"
  });
});
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Jon2 AI server listening on port ${PORT}`);
});
