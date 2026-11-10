const MODEL = "@cf/zai-org/glm-4.7-flash";
const MAX_BODY = 180_000;
const MAX_FILES = 40;
const MAX_CONTEXT = 70_000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    }
  });
}

function decodePart(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(normalized), c => c.charCodeAt(0));
}

async function verifyAccess(request, env) {
  if (!env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD) return { configured: false };
  const token = request.headers.get("cf-access-jwt-assertion");
  if (!token) return { configured: true, valid: false };

  try {
    const parts = token.split(".");
    if (parts.length !== 3) return { configured: true, valid: false };
    const header = JSON.parse(new TextDecoder().decode(decodePart(parts[0])));
    const claims = JSON.parse(new TextDecoder().decode(decodePart(parts[1])));
    const now = Math.floor(Date.now() / 1000);
    const team = String(env.ACCESS_TEAM_DOMAIN).replace(/^https?:\\/\\//, "").replace(/\\/$/, "");
    if (claims.iss !== "https://" + team) return { configured: true, valid: false };
    if (!Array.isArray(claims.aud) || !claims.aud.includes(env.ACCESS_AUD)) return { configured: true, valid: false };
    if (typeof claims.exp !== "number" || claims.exp <= now) return { configured: true, valid: false };
    if (typeof claims.nbf === "number" && claims.nbf > now + 60) return { configured: true, valid: false };

    const certResponse = await fetch("https://" + team + "/cdn-cgi/access/certs", { cf: { cacheTtl: 300 } });
    if (!certResponse.ok) return { configured: true, valid: false };
    const certs = await certResponse.json();
    const jwk = (certs.keys || []).find(key => key.kid === header.kid);
    if (!jwk || header.alg !== "RS256") return { configured: true, valid: false };
    const publicKey = await crypto.subtle.importKey(
      "jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]
    );
    const valid = await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5", publicKey, decodePart(parts[2]),
      new TextEncoder().encode(parts[0] + "." + parts[1])
    );
    return { configured: true, valid };
  } catch {
    return { configured: true, valid: false };
  }
}

function validPath(path) {
  return typeof path === "string" &&
    path.length <= 100 &&
    /^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(path) &&
    !path.startsWith("/") &&
    !path.split("/").some(part => !part || part === "." || part === "..") &&
    !path.split("/").some(part => part.startsWith("."));
}

function extractToolCall(result) {
  const response = result && result.response;
  const calls = response && response.tool_calls || result && result.tool_calls;
  if (Array.isArray(calls) && calls.length) {
    const call = calls.find(item => item.function && item.function.name === "submit_agent_result") || calls[0];
    const args = call && call.function && call.function.arguments;
    if (typeof args === "string") return JSON.parse(args);
    if (args && typeof args === "object") return args;
  }
  return null;
}

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get("origin");
  const requestOrigin = new URL(request.url).origin;
  if (origin && origin !== requestOrigin) return json({ error: "الطلب من مصدر غير مسموح." }, 403);

  const access = await verifyAccess(request, env);
  if (!access.configured) {
    return json({ error: "لم يتم إعداد حماية Cloudflare Access بعد. لن يتم تشغيل الذكاء قبل حماية الاستوديو." }, 503);
  }
  if (!access.valid) return json({ error: "يجب تسجيل الدخول عبر Cloudflare Access لاستخدام Jon2 Bot." }, 401);
  if (!env.AI || typeof env.AI.run !== "function") {
    return json({ error: "ربط Workers AI غير مفعّل في إعدادات Pages." }, 503);
  }

  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BODY) return json({ error: "حجم الطلب أكبر من الحد المسموح." }, 413);

  let body;
  try { body = await request.json(); } catch { return json({ error: "بيانات الطلب غير صالحة." }, 400); }
  const task = typeof body.task === "string" ? body.task.trim().slice(0, 4000) : "";
  const files = body.files && typeof body.files === "object" && !Array.isArray(body.files) ? body.files : {};
  if (!task) return json({ error: "اكتب المطلوب من Jon2 Bot." }, 400);

  const names = Object.keys(files).slice(0, MAX_FILES);
  const safeFiles = {};
  let total = 0;
  for (const name of names) {
    const file = files[name];
    if (!validPath(name) || !file || typeof file.content !== "string") continue;
    const remaining = MAX_CONTEXT - total;
    if (remaining <= 0) break;
    const content = file.content.slice(0, Math.min(18_000, remaining));
    safeFiles[name] = content;
    total += content.length;
  }

  const history = Array.isArray(body.history) ? body.history.slice(-8).map(item => ({
    role: item && item.role === "assistant" ? "assistant" : "user",
    content: String(item && item.content || "").slice(0, 2500)
  })) : [];

  const system = [
    "أنت Jon2 Bot، وكيل برمجة عربي مدمج داخل Jon2 Studio.",
    "مهمتك فهم طلب المستخدم والعمل على ملفات مشروعه الحالية. اقرأ الملفات المقدمة قبل التعديل، واحتفظ بالتصميم والسلوك الموجودين ما لم يطلب المستخدم تغييره.",
    "يمكنك إنشاء ملفات جديدة أو تحديث ملفات موجودة. لا تحذف ملفات. لا تنفذ أوامر نظام أو شبكات أو تثبيت حزم. لا تدّع أنك شغّلت اختبارات حقيقية؛ يمكنك مراجعة الكود ذهنيًا فقط.",
    "أعد دائمًا استدعاء الدالة submit_agent_result مرة واحدة. ضع شرحًا عربيًا موجزًا في message، والتغييرات الكاملة للملفات في files. إذا كان الطلب سؤالًا أو شرحًا فقط، اجعل files مصفوفة فارغة.",
    "كل عنصر في files يجب أن يحتوي path وcontent. اكتب المحتوى الكامل للملف وليس رقعة جزئية. لا تستخدم مسارات تبدأ بنقطة أو تحتوي على .. أو / في البداية.",
    "لا تستبدل ملفًا إلا إذا كان ذلك مطلوبًا. لا تكتب مفاتيح سرية أو كلمات مرور أو بيانات شخصية في الملفات. إذا كان الطلب غامضًا لدرجة تمنع التعديل الآمن، اسأل سؤالًا واحدًا واجعل files فارغة.",
    "اكتب HTML/CSS/JavaScript متوافقًا مع المتصفح. في صفحات الويب استخدم العربية وRTL افتراضيًا ما لم يطلب المستخدم خلاف ذلك. لا تستخدم مكتبات خارجية إلا إذا طلبها المستخدم أو كانت موجودة بالفعل في المشروع.",
    "المعاينة تعمل في iframe معزول؛ لا تفترض توفر backend أو ملفات نظام أو Python/Node runtime."
  ].join("\n");

  const userPayload = JSON.stringify({
    task,
    projectFiles: safeFiles,
    note: "الملفات الحالية هي مصدر الحقيقة. أعد فقط الملفات التي تريد إنشاءها أو تحديثها."
  });

  try {
    const result = await env.AI.run(MODEL, {
      messages: [
        { role: "system", content: system },
        ...history,
        { role: "user", content: userPayload }
      ],
      tools: [{
        type: "function",
        function: {
          name: "submit_agent_result",
          description: "Return the Arabic response and complete file contents to create or update in the user's project.",
          parameters: {
            type: "object",
            properties: {
              message: { type: "string" },
              files: {
                type: "array",
                maxItems: 12,
                items: {
                  type: "object",
                  properties: {
                    path: { type: "string" },
                    content: { type: "string" }
                  },
                  required: ["path", "content"]
                }
              }
            },
            required: ["message", "files"]
          }
        }
      }],
      tool_choice: { type: "function", function: { name: "submit_agent_result" } },
      max_tokens: 12000,
      temperature: 0.2
    });

    const proposal = extractToolCall(result);
    if (!proposal || typeof proposal.message !== "string" || !Array.isArray(proposal.files)) {
      return json({ error: "لم يرجع النموذج خطة قابلة للتطبيق. جرّب صياغة الطلب بشكل أوضح." }, 502);
    }

    if (proposal.files.length > 12) return json({ error: "عدد الملفات المقترح أكبر من الحد الآمن." }, 422);
    const changes = [];
    let outputSize = 0;
    for (const file of proposal.files) {
      if (!file || !validPath(file.path) || typeof file.content !== "string" || file.content.length > 100_000) {
        return json({ error: "تضمن اقتراح الذكاء ملفًا أو مسارًا غير صالح؛ لم يتم تطبيق أي تغيير." }, 422);
      }
      outputSize += file.content.length;
      if (outputSize > 500_000) return json({ error: "حجم التغييرات المقترحة أكبر من الحد الآمن." }, 422);
      changes.push({ path: file.path, content: file.content });
    }

    return json({
      message: proposal.message.slice(0, 6000),
      changes,
      model: MODEL,
      applied: false
    });
  } catch (error) {
    return json({
      error: "تعذر إكمال طلب الذكاء الآن. قد تكون الحصة المجانية اليومية انتهت أو أن النموذج غير متاح مؤقتًا.",
      detail: String(error && error.message || error).slice(0, 300)
    }, 503);
  }
}

export async function onRequestGet({ request, env }) {
  const access = await verifyAccess(request, env);
  if (!access.configured) return json({ service: "Jon2 Studio Agent", status: "needs_access_configuration" }, 503);
  if (!access.valid) return json({ error: "يجب تسجيل الدخول عبر Cloudflare Access." }, 401);
  if (!env.AI || typeof env.AI.run !== "function") {
    return json({ service: "Jon2 Studio Agent", status: "needs_workers_ai_binding" }, 503);
  }
  return json({ service: "Jon2 Studio Agent", status: "ready", model: MODEL });
}
