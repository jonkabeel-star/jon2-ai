"use strict";
const http = require("http");
const PORT = Number(process.env.PORT) || 3000;
// عنوان خادم نموذج Jon2 AI الحقيقي
const AI_MODEL_URL = process.env.AI_MODEL_URL || "";
function send(res, status, data) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
  });
  res.end(JSON.stringify(data));
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk;
      if (body.length > 100000) {
        reject(new Error("حجم الرسالة كبير جدًا."));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        reject(new Error("بيانات الطلب غير صالحة."));
      }
    });
    req.on("error", reject);
  });
}
async function askModel(message) {
  if (!AI_MODEL_URL) {
    const error = new Error(
      "نموذج الذكاء الاصطناعي غير متصل. يجب إعداد عنوان خادم النموذج أولًا."
    );
    error.status = 503;
    throw error;
  }
  const response = await fetch(AI_MODEL_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message,
      prompt: message
    }),
    signal: AbortSignal.timeout(120000)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      data.error || "خادم نموذج الذكاء الاصطناعي لم يستطع الإجابة."
    );
    error.status = 502;
    throw error;
  }
  const reply =
    data.reply ??
    data.response ??
    data.generated_text ??
    data.text ??
    data.choices?.[0]?.message?.content;
  if (typeof reply !== "string" || !reply.trim()) {
    const error = new Error(
      "الخادم لم يُرجع إجابة نصية مفهومة."
    );
    error.status = 502;
    throw error;
  }
  return reply.trim();
}
const server = http.createServer(async (req, res) => {
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
  const url = new URL(
    req.url,
    `http://${req.headers.host || "localhost"}`
  );
  if (url.pathname === "/api/health" && req.method === "GET") {
    return send(res, 200, {
      project: "Jon2 AI",
      status: "online",
      aiEngine: AI_MODEL_URL ? "configured" : "not_connected",
      chatEndpoint: "/api/chat"
    });
  }
  if (url.pathname === "/api/chat" && req.method === "POST") {
    let body;
    try {
      body = await readBody(req);
    } catch (error) {
      return send(res, 400, {
        error: error.message || "تعذر قراءة الرسالة."
      });
    }
    if (
      typeof body.message !== "string" ||
      !body.message.trim()
    ) {
      return send(res, 400, {
        error: "اكتب رسالتك أولًا."
      });
    }
    try {
      const reply = await askModel(body.message.trim());
      return send(res, 200, {
        project: "Jon2 AI",
        reply
      });
    } catch (error) {
      console.error("Jon2 AI model error:", error.message);
      return send(res, error.status || 502, {
        error: error.message || "تعذر الاتصال بنموذج الذكاء الاصطناعي."
      });
    }
  }
  return send(res, 404, {
    error: "المسار المطلوب غير موجود."
  });
});
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Jon2 AI server listening on port ${PORT}`);
});
