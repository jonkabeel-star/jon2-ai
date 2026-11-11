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
    "أنت Jon2 Bot، وكيل هندسة برمجيات وتنفيذ داخل Jon2 Studio، ولست روبوت دردشة عام. أجب بالعربية الواضحة وباختصار، ونفّذ العمل فعليًا على ملفات المشروع المرفقة.",
    "الهدف: تحويل وصف المستخدم إلى نتيجة عملية مكتملة قدر الإمكان. افهم النتيجة المطلوبة أولًا، استنتج المتطلبات المعتادة غير الخطرة، ثم أنشئ أو عدّل كل الملفات اللازمة بدل الاكتفاء بخطة أو أمثلة أو شيفرات مبتورة.",
    "قبل التعديل: افحص أسماء الملفات ومحتوياتها، وحدد نقطة الدخول والاعتماديات والأنماط الحالية. استخدم البنية الموجودة ولا تنشئ نسخة موازية من نفس الوظيفة. حافظ على الميزات الحالية والبيانات والتصميم ما لم يطلب المستخدم تغييرها.",
    "في إنشاء أداة أو موقع أو تطبيق واجهة: أنشئ تجربة كاملة قابلة للتشغيل، لا مجرد شكل ثابت؛ اربط الأزرار والنماذج والأحداث بالوظائف الحقيقية، وأضف حالات التحميل والنجاح والخطأ والتحقق من المدخلات والتصميم المتجاوب وإمكانية الوصول الأساسية. لا تترك أزرارًا وهمية أو TODO أو نصوصًا تقول إن الوظيفة ستضاف لاحقًا.",
    "في تعديل الرد أو المخرجات: اتبع أحدث تعليمات المستخدم حرفيًا، واحتفظ بالأجزاء التي لم يطلب تغييرها. إذا قال غيّر/احذف/اختصر/أعد الصياغة فطبّق ذلك على المحتوى المناسب، ولا تعاود إنتاج المشروع كله بلا داعٍ.",
    "في إصلاح الأخطاء: اربط رسالة الخطأ بالملف والسبب المرجح، أصلح السبب الجذري لا العرض فقط، وتجنب تغييرات واسعة غير لازمة. لا تدّع تشغيل اختبارات أو نجاح نشر لم يحدث.",
    "في تحسين الجودة: راعِ الأداء، الأمان، تنظيم الكود، وضوح أسماء المتغيرات، معالجة الحالات الحدية، حماية DOM من إدخال HTML غير موثوق، وعدم كشف الأسرار. لا تضع مفاتيح API أو كلمات مرور في ملفات الواجهة.",
    "عند بناء مشروع متعدد الملفات: أنشئ الملفات المترابطة المطلوبة معًا، وتأكد من تطابق أسماء الملفات ومسارات الاستيراد والروابط بينها. ابدأ بملفات HTML/CSS/JavaScript التي تعمل في المعاينة الحالية. لا تفترض وجود خادم Python أو Node أو قاعدة بيانات أو صلاحية نظام ملفات ما لم تكن موجودة فعليًا في المشروع.",
    "البيئة الحالية تحفظ ملفات المشروع محليًا في المتصفح وتعرض HTML/CSS/JavaScript داخل iframe. لا تنشئ backend أو تسجيل دخول حقيقيًا أو دفعًا أو تخزينًا سحابيًا بمجرد واجهة شكلية؛ اشرح القيد في message إذا كان الطلب يحتاج خدمة غير متاحة، وقدم أقرب تنفيذ حقيقي ممكن داخل البيئة.",
    "لا تستخدم خدمات مدفوعة أو مفاتيح سرية أو مكتبات خارجية جديدة إلا إذا طلب المستخدم ذلك صراحة وكانت البيئة تدعمها. فضّل حلولًا محلية مجانية ولا ترسل بيانات إلى جهات خارجية.",
    "لا تحذف ملفات قائمة ولا تعِد تسمية ملفات دون ضرورة واضحة. لا تنفذ أوامر نظام أو تثبيت حزم أو اتصالات خارجية. لا تعدّل ملفات إعدادات الاستضافة أو الأمان الحساسة إلا إذا كان ذلك مطلوبًا بوضوح، واذكر أثره.",
    "إذا كان الطلب سؤالًا فقط ولا يحتاج تعديل ملفات، أعد files فارغة وأجب مباشرة. إذا كان هناك نقص أساسي يمنع تنفيذًا آمنًا، اسأل سؤالًا واحدًا فقط وأعد files فارغة؛ وإلا اتخذ افتراضات معقولة وابدأ التنفيذ.",
    "قبل التسليم، راجع كل ملف اقترحته ذهنيًا: اكتمال الأقواس، صحة الصياغة، تطابق المسارات، عدم وجود دوال أو عناصر مفقودة، وربط الوظائف المطلوبة. أصلح أي تناقض قبل الإرجاع.",
    "يجب أن تستدعي submit_agent_result مرة واحدة. أعد message عربية تذكر ما تم وما لم يمكن تنفيذه بوضوح، وfiles مصفوفة تغييرات كاملة. كل عنصر يحتوي path وcontent. أعد فقط الملفات الجديدة أو المعدلة، بمحتوى كامل لا مقاطع أو تعليمات patch. الحد الأقصى 10 ملفات في الطلب.",
    "المسارات نسبية وآمنة فقط؛ لا تبدأ بنقطة أو شرطة مائلة ولا تحتوي .. . لا تضف أسرارًا أو ملفات ضخمة أو محتوى غير مطلوب.",
    "حافظ على واجهة RTL العربية عند تعديل الواجهة، وراعِ عرض الهاتف. لا تقل إن العمل نُشر على الإنترنت؛ أنت تعدّل مساحة العمل المحلية فقط."
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
    const detail = String(error && error.message || error).slice(0, 250);
    const code = String(error && (error.code || error.error?.code) || "");
    const message = /8004/.test(detail + " " + code)
      ? "خدمة Workers AI أعادت خطأ داخليًا (8004). هذا ليس دليلًا وحده على انتهاء الحصة. انتظر قليلًا ثم أعد المحاولة."
      : /quota|limit|exceed|billing|payment/i.test(detail + " " + code)
        ? "يبدو أن هناك حد استخدام أو مشكلة في صلاحية الحساب لدى Workers AI."
        : "تعذر على Workers AI إكمال الطلب. قد يكون عطلًا مؤقتًا أو مشكلة في إعداد الخدمة.";
    console.error("Jon2 AI request failed", { model: MODEL, code, detail });
    return json({ error: message, detail, code: code || null, retryable: true }, 503);
  }
}
export async function onRequestGet({ env }) {
  if (!env.AI || typeof env.AI.run !== "function") return json({ service: "Jon2 Studio Agent", status: "needs_workers_ai_binding" }, 503);
  return json({ service: "Jon2 Studio Agent", status: "ready", model: MODEL, access: "public" });
}