"use strict";

// Jon2 AI API gateway.
// Security defaults: explicit CORS allowlist, bounded request bodies,
// simple per-process rate limiting, and server-side model URL configuration.
// Production authentication and shared rate limiting must be added before public launch.

const http = require("http");
const crypto = require("crypto");
const auth = require("./auth");

const PORT = Number(process.env.PORT) || 3000;
const AI_MODEL_URL = (process.env.AI_MODEL_URL || "").trim();
const DEFAULT_ORIGIN = "https://jonkabeel-star.github.io";
const ALLOWED_ORIGINS = new Set(
  (process.env.JON2_ALLOWED_ORIGINS || DEFAULT_ORIGIN)
    .split(",")
    .map(value => value.trim())
    .filter(Boolean)
);
const MAX_BODY_BYTES = 16 * 1024;
const RATE_WINDOW_MS = 60 * 1000;
const RATE_MAX_REQUESTS = 12;
const TRUST_PROXY = process.env.TRUST_PROXY === "true";
const requestBuckets = new Map();

function send(res, status, data) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer"
  });
  res.end(JSON.stringify(data));
}

function applyCors(req, res) {
  const origin = req.headers.origin;
  if (!origin) return true;
  const forwardedProto = req.headers["x-forwarded-proto"];
  const requestProtocol = typeof forwardedProto === "string"
    ? forwardedProto.split(",")[0].trim()
    : (req.socket.encrypted ? "https" : "http");
  let sameOrigin = false;
  try {
    const parsedOrigin = new URL(origin);
    sameOrigin = parsedOrigin.host === req.headers.host && parsedOrigin.protocol === `${requestProtocol}:`;
  } catch {}
  if (sameOrigin) return true;
  if (ALLOWED_ORIGINS.has(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token");
    res.setHeader("Access-Control-Allow-Credentials", "true");
    return true;
  }
  return false;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    let bytes = 0;
    req.on("data", chunk => {
      bytes += chunk.length;
      if (bytes > MAX_BODY_BYTES) {
        reject(Object.assign(new Error("حجم الطلب أكبر من الحد المسموح."), { status: 413 }));
        req.destroy();
        return;
      }
      body += chunk.toString("utf8");
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        reject(Object.assign(new Error("بيانات الطلب غير صالحة."), { status: 400 }));
      }
    });
    req.on("error", reject);
  });
}

function allowRequest(req) {
  const forwarded = TRUST_PROXY ? req.headers["x-forwarded-for"] : null;
  const ip = (typeof forwarded === "string" ? forwarded.split(",")[0].trim() : req.socket.remoteAddress) || "unknown";
  const now = Date.now();
  if (!requestBuckets.has(ip) && requestBuckets.size >= 5000) {
    for (const [key, value] of requestBuckets) {
      if (now - value.startedAt >= RATE_WINDOW_MS) requestBuckets.delete(key);
    }
    if (requestBuckets.size >= 5000) return false;
  }
  const current = requestBuckets.get(ip);
  if (!current || now - current.startedAt >= RATE_WINDOW_MS) {
    requestBuckets.set(ip, { startedAt: now, count: 1 });
    return true;
  }
  if (current.count >= RATE_MAX_REQUESTS) return false;
  current.count += 1;
  return true;
}

async function askModel(message) {
  if (!AI_MODEL_URL) {
    throw Object.assign(
      new Error("نموذج الذكاء الاصطناعي غير متصل. لم يتم إعداد AI_MODEL_URL."),
      { status: 503 }
    );
  }

  const response = await fetch(AI_MODEL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, prompt: message }),
    signal: AbortSignal.timeout(90000)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw Object.assign(new Error("تعذر على خادم النموذج معالجة الطلب."), { status: 502 });
  }
  const reply =
    data.reply ??
    data.response ??
    data.generated_text ??
    data.text ??
    data.choices?.[0]?.message?.content;
  if (typeof reply !== "string" || !reply.trim()) {
    throw Object.assign(new Error("لم يُرجع نموذج الذكاء الاصطناعي إجابة صالحة."), { status: 502 });
  }
  return reply.trim();
}

const server = http.createServer(async (req, res) => {
  const corsAllowed = applyCors(req, res);
  if (!corsAllowed) return send(res, 403, { error: "هذا المصدر غير مسموح له بالاتصال." });
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }

  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  if (url.pathname === "/api/health" && req.method === "GET") {
    return send(res, 200, {
      project: "Jon2 AI",
      status: "online",
      aiEngine: AI_MODEL_URL ? "configured" : "not_connected",
      authentication: auth.configured() ? "configured_not_yet_security_reviewed" : "not_configured",
      publicLaunchReady: false
    });
  }

  if (url.pathname === "/api/auth/verify" && req.method === "GET") {
    const token = url.searchParams.get("token") || "";
    if (token.length < 30 || token.length > 100) {
      return send(res, 400, { error: "رابط التأكيد غير صالح أو منتهي." });
    }
    res.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Referrer-Policy": "no-referrer",
      "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    });
    return res.end(`<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>تأكيد Jon2 AI</title><body style="font-family:Arial,sans-serif;padding:32px;max-width:520px;margin:auto"><h2>تأكيد بريدك الإلكتروني</h2><p>اضغط الزر لتأكيد حساب Jon2 AI.</p><button id="verify" style="padding:12px 20px;background:#6385ff;color:white;border:0;border-radius:10px">تأكيد البريد</button><p id="result" role="status"></p><script>const token=${JSON.stringify(token)};document.getElementById("verify").addEventListener("click",async()=>{const b=document.getElementById("verify"),o=document.getElementById("result");b.disabled=true;try{const r=await fetch("/api/auth/verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token})});const d=await r.json();o.textContent=r.ok?"تم تأكيد بريدك الإلكتروني. يمكنك الآن العودة إلى موقع Jon2 AI وتسجيل الدخول.":(d.error||"تعذر تأكيد البريد.");}catch{o.textContent="تعذر الاتصال. حاول مرة أخرى.";}finally{b.disabled=false;}});</script></body></html>`);
  }

  if (url.pathname === "/api/auth/verify" && req.method === "POST") {
    try {
      const body = await readBody(req);
      await auth.verifyEmail(body.token || "");
      return send(res, 200, { verified: true, message: "تم تأكيد البريد الإلكتروني." });
    } catch (error) {
      return send(res, error.status || 503, { error: error.message || "تعذر تأكيد البريد." });
    }
  }

  if (url.pathname === "/api/auth/register" && req.method === "POST") {
    if (!allowRequest(req)) return send(res, 429, { error: "طلبات كثيرة. حاول بعد دقيقة." });
    try {
      const body = await readBody(req);
      const result = await auth.register(body.email, body.password);
      return send(res, 202, result);
    } catch (error) {
      return send(res, error.status || 503, { error: error.status ? error.message : "تعذر إنشاء الحساب الآن." });
    }
  }

  if (url.pathname === "/api/auth/resend-verification" && req.method === "POST") {
    if (!allowRequest(req)) return send(res, 429, { error: "طلبات كثيرة. حاول بعد دقيقة." });
    try {
      const body = await readBody(req);
      const result = await auth.resendVerification(body.email);
      return send(res, 202, result);
    } catch (error) {
      return send(res, error.status || 503, { error: error.status ? error.message : "تعذر إرسال رسالة التأكيد." });
    }
  }

  if (url.pathname === "/api/auth/login" && req.method === "POST") {
    if (!allowRequest(req)) return send(res, 429, { error: "طلبات كثيرة. حاول بعد دقيقة." });
    try {
      const body = await readBody(req);
      const result = await auth.login(body.email, body.password, res);
      return send(res, 200, result);
    } catch (error) {
      return send(res, error.status || 503, { error: error.status ? error.message : "تعذر تسجيل الدخول الآن." });
    }
  }

  if (url.pathname === "/api/auth/me" && req.method === "GET") {
    try {
      const result = await auth.rotateCsrf(req);
      return send(res, 200, result);
    } catch (error) {
      return send(res, error.status || 503, { error: error.message || "تعذر قراءة الجلسة." });
    }
  }

  if (url.pathname === "/api/auth/logout" && req.method === "POST") {
    try {
      const result = await auth.logout(req, res);
      return send(res, 200, result);
    } catch (error) {
      return send(res, error.status || 503, { error: error.message || "تعذر إنهاء الجلسة." });
    }
  }

  if (url.pathname === "/api/chat" && req.method === "POST") {
    try {
      const session = await auth.currentSession(req);
      if (!session) return send(res, 401, { error: "سجّل الدخول لاستخدام أدوات Jon2 AI." });
      await auth.requireCsrf(req, session);
    } catch (error) {
      return send(res, error.status || 503, { error: error.message || "تعذر التحقق من الجلسة." });
    }
    if (!allowRequest(req)) {
      return send(res, 429, { error: "طلبات كثيرة خلال وقت قصير. حاول بعد دقيقة." });
    }

    let body;
    try {
      body = await readBody(req);
    } catch (error) {
      return send(res, error.status || 400, { error: error.message || "تعذر قراءة الطلب." });
    }

    if (typeof body.message !== "string" || !body.message.trim()) {
      return send(res, 400, { error: "اكتب رسالتك أولًا." });
    }
    if (body.message.length > 4000) {
      return send(res, 413, { error: "الرسالة طويلة جدًا؛ الحد الأقصى 4000 حرف." });
    }

    try {
      const reply = await askModel(body.message.trim());
      return send(res, 200, { project: "Jon2 AI", reply });
    } catch (error) {
      const status = error.status || 502;
      const reference = crypto.randomUUID();
      console.error("Jon2 AI model failure", { reference, message: error.message });
      return send(res, status, {
        error: status === 503 ? error.message : "تعذر إكمال الطلب الآن.",
        reference
      });
    }
  }

  return send(res, 404, { error: "المسار المطلوب غير موجود." });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Jon2 AI API gateway listening on port ${PORT}`);
});
