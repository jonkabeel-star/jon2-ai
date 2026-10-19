const http = require("http");
const crypto = require("crypto");

const PORT = process.env.PORT || 3000;

// نموذج أولي: المفاتيح محفوظة في الذاكرة فقط
const apiKeys = new Map();

const server = http.createServer((req, res) => {
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

  // فحص حالة الخادم
  if (req.url === "/api/health" && req.method === "GET") {
    res.writeHead(200);
    return res.end(JSON.stringify({
      project: "Jon2 AI",
      status: "online",
      message: "Jon2 AI server is running",
      aiEngine: "not_connected"
    }));
  }

  // إنشاء مفتاح API جديد
  if (req.url === "/api/keys" && req.method === "POST") {
    const chunks = [];

    req.on("data", chunk => chunks.push(chunk));

    req.on("end", () => {
      let body = {};

      try {
        body = JSON.parse(Buffer.concat(chunks).toString() || "{}");
      } catch {
        res.writeHead(400);
        return res.end(JSON.stringify({
          error: "Invalid JSON"
        }));
      }

      // يتطلب سرًا خاصًا محفوظًا في إعدادات الخادم
      const adminSecret = process.env.JON2_ADMIN_SECRET;

      if (!adminSecret || body.adminSecret !== adminSecret) {
        res.writeHead(403);
        return res.end(JSON.stringify({
          error: "Not authorized to create API keys"
        }));
      }

      const key = "jon2_sk_" + crypto.randomBytes(32).toString("hex");

      apiKeys.set(crypto.createHash("sha256").update(key).digest("hex"), {
        createdAt: new Date().toISOString()
      });

      res.writeHead(201);
      return res.end(JSON.stringify({
        project: "Jon2 AI",
        apiKey: key,
        warning: "Save this key securely. It will not be shown again."
      }));
    });

    return;
  }

  // التحقق من صلاحية مفتاح API
  if (req.url === "/api/keys/verify" && req.method === "POST") {
    const auth = req.headers.authorization || "";
    const key = auth.startsWith("Bearer ") ? auth.slice(7) : "";

    if (!key.startsWith("jon2_sk_")) {
      res.writeHead(401);
      return res.end(JSON.stringify({
        valid: false,
        error: "Missing or invalid API key"
      }));
    }

    const hash = crypto.createHash("sha256").update(key).digest("hex");
    const valid = apiKeys.has(hash);

    res.writeHead(valid ? 200 : 401);
    return res.end(JSON.stringify({ valid }));
  }

  res.writeHead(404);
  return res.end(JSON.stringify({
    error: "Endpoint not found"
  }));
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Jon2 AI server listening on port ${PORT}`);
});
