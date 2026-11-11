const MODEL = "@cf/zai-org/glm-4.7-flash";
const MAX_BODY = 180_000;
const MAX_FILES = 10;
const MAX_CONTEXT = 20_000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff"
  }});
}
function validPath(path) {
  return typeof path === "string" && path.length <= 100 &&
    /^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(path) && !path.startsWith("/") &&
    !path.split("/").some(part => !part || part === "." || part === ".." || part.startsWith("."));
}
function extractToolCall(result) {
  const response = result && result.response;
  const choice = result && result.choices && result.choices[0];
  const responseChoice = response && response.choices && response.choices[0];
  const message = choice && choice.message || responseChoice && responseChoice.message;
  const calls = choice && choice.message && choice.message.tool_calls ||
    responseChoice && responseChoice.message && responseChoice.message.tool_calls ||
    response && response.tool_calls || result && result.tool_calls || message && message.tool_calls;
  if (Array.isArray(calls) && calls.length) {
    const call = calls.find(item => item.function && item.function.name === "submit_agent_result") || calls[0];
    const args = call && call.function && call.function.arguments;
    if (typeof args === "string") {
      try { const parsed = JSON.parse(args); if (parsed && typeof parsed === "object") return parsed; } catch {}
    } else if (args && typeof args === "object") return args;
  }
  const text = message && typeof message.content === "string" ? message.content :
    typeof response === "string" ? response :
    typeof result?.output_text === "string" ? result.output_text : "";
  if (text) {
    const cleaned = text.trim().replace(/^\x60{3}(?:json)?\s*/i, "").replace(/\s*\x60{3}$/i, "");
    try {
      const parsed = JSON.parse(cleaned);
      if (parsed && typeof parsed.message === "string" && Array.isArray(parsed.files)) return parsed;
    } catch {}
    return { message: cleaned.slice(0, 5000), files: [] };
  }
  return null;
}
export async function onRequestPost({ request, env }) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) return json({ error: "الطلب من مصدر غير مسموح." }, 403);
  if (!env.AI || typeof env.AI.run !== "function") return json({ error: "ربط Workers AI غير مفعّل في إعدادات Pages." }, 503);
  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BODY) return json({ error: "حجم الطلب أكبر من الحد المسموح." }, 413);
  let body;
  try { body = await request.json(); } catch { return json({ error: "بيانات الطلب غير صالحة." }, 400); }
  const task = typeof body.task === "string" ? body.task.trim().slice(0, 4000) : "";
  const files = body.files && typeof body.files === "object" && !Array.isArray(body.files) ? body.files : {};
  if (!task) return json({ error: "اكتب المطلوب من Jon2 Bot." }, 400);

  const preferred = typeof body.activeFile === "string" ? body.activeFile : "";
  const names = [...new Set([preferred, ...Object.keys(files)])].filter(Boolean).slice(0, MAX_FILES);
  const safeFiles = {};
  let total = 0;
  for (const name of names) {
    const file = files[name];
    if (!validPath(name) || !file || typeof file.content !== "string") continue;
    const remaining = MAX_CONTEXT - total;
    if (remaining <= 0) break;
    const limit = name === preferred ? 9000 : 2200;
    safeFiles[name] = file.content.slice(0, Math.min(limit, remaining));
    total += safeFiles[name].length;
  }
  const history = Array.isArray(body.history) ? body.history.slice(-4).map(item => ({
    role: item && item.role === "assistant" ? "assistant" : "user",
    content: String(item && item.content || "").slice(0, 500)
  })) : [];

  const system = [
    "أنت Jon2 Bot، مهندس برمجيات ومساعد برمجة عملي داخل Jon2 Studio. أجب بالعربية.",
    "نفذ طلب المستخدم على ملفات المشروع المرفقة. اقرأ الملفات ذات الصلة وافهم بنية المشروع قبل اقتراح التغييرات.",
    "عند طلب إنشاء أو تعديل برنامج: أعد الملفات الكاملة اللازمة في files، لا تكتف بخطة أو وصف أو قول سأفعل. لا تغيّر الملفات غير المرتبطة بالطلب.",
    "عند طلب إصلاح: حدد السبب من الكود المرفق وأصلح السبب الحقيقي مع الحفاظ على السلوك الحالي. عند تحسين الأداء: قلل العمل غير الضروري وحافظ على الوظائف. عند مراجعة الأمان: لا تضف أسرارًا أو مفاتيح.",
    "لا تخترع ملفات أو APIs أو مكتبات غير موجودة. لا تفترض وجود خادم خلفي أو Python أو Node في المعاينة. استخدم HTML وCSS وJavaScript المتوافقة مع المتصفح عند الحاجة.",
    "إذا كان الطلب سؤالًا فقط ولا يحتاج تغيير ملفات، أعد files فارغة وأجب مباشرة. إذا كان هناك نقص حقيقي يمنع التعديل الآمن، اسأل سؤالًا واحدًا واضحًا وأعد files فارغة.",
    "لا تحذف ملفات ولا تنفذ أوامر نظام أو تثبيت حزم أو اتصالات خارجية. لا تدّع تشغيل اختبارات لم تنفذها.",
    "يجب أن تستدعي submit_agent_result مرة واحدة. message شرح موجز للنتيجة، وfiles مصفوفة تغييرات كاملة. كل عنصر يحتوي path وcontent. لا تستخدم مسارات تبدأ بنقطة أو تحتوي .. أو تبدأ بشرطة مائلة.",
    "حافظ على واجهة RTL العربية عند تعديل الواجهة، وراعِ عرض الهاتف. لا تضف اعتماديات خارجية إلا إذا كانت موجودة أصلًا أو طلبها المستخدم."
  ].join("\n");
  const userPayload = JSON.stringify({ task, projectFiles: safeFiles, note: "هذه هي الملفات الحالية ذات الصلة. أعد الملفات التي تريد إنشاءها أو تحديثها فقط." });
  try {
    const result = await env.AI.run(MODEL, {
      messages: [{ role: "system", content: system }, ...history, { role: "user", content: userPayload }],
      tools: [{
        type: "function",
        function: {
          name: "submit_agent_result",
          description: "Return a concise Arabic result and complete contents of project files to create or update.",
          parameters: {
            type: "object",
            properties: {
              message: { type: "string" },
              files: { type: "array", maxItems: 10, items: {
                type: "object", properties: { path: { type: "string" }, content: { type: "string" } },
                required: ["path", "content"]
              }}
            },
            required: ["message", "files"]
          }
        }
      }],
      tool_choice: { type: "function", function: { name: "submit_agent_result" } },
      max_tokens: 5200,
      temperature: 0.15,
      chat_template_kwargs: { enable_thinking: false }
    });
    const proposal = extractToolCall(result);
    if (!proposal || typeof proposal.message !== "string" || !Array.isArray(proposal.files)) {
      return json({ error: "لم يرجع النموذج محتوى قابلًا للتطبيق. جرّب طلبًا محددًا أو أعد المحاولة." }, 502);
    }
    if (proposal.files.length > 10) return json({ error: "عدد الملفات المقترح أكبر من الحد الآمن." }, 422);
    const changes = [];
    let outputSize = 0;
    for (const file of proposal.files) {
      if (!file || !validPath(file.path) || typeof file.content !== "string" || file.content.length > 100_000)
        return json({ error: "تضمن الاقتراح ملفًا أو مسارًا غير صالح؛ لم يتم تطبيق أي تغيير." }, 422);
      outputSize += file.content.length;
      if (outputSize > 400_000) return json({ error: "حجم التغييرات أكبر من الحد الآمن." }, 422);
      changes.push({ path: file.path, content: file.content });
    }
    return json({ message: proposal.message.slice(0, 5000), changes, model: MODEL, applied: false });
  } catch (error) {
    return json({ error: "تعذر إكمال طلب الذكاء الآن. قد تكون الحصة اليومية انتهت أو أن النموذج غير متاح مؤقتًا.", detail: String(error && error.message || error).slice(0, 250) }, 503);
  }
}
export async function onRequestGet({ env }) {
  if (!env.AI || typeof env.AI.run !== "function") return json({ service: "Jon2 Studio Agent", status: "needs_workers_ai_binding" }, 503);
  return json({ service: "Jon2 Studio Agent", status: "ready", model: MODEL, access: "public" });
}