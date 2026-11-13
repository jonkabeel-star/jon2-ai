// Local open-weight chat for iPhone Safari.
// Runtime and model weights are downloaded from public CDNs/Hugging Face.
// User prompts are processed by the in-browser model; no inference API is called.
const MODEL_ID = "onnx-community/Qwen2.5-0.5B-Instruct";
const MODEL_REVISION = "516c8d0";
const TRANSFORMERS_URL = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0";

let generatorPromise = null;
let generator = null;
const byId = id => document.getElementById(id);
const isArabic = () => document.documentElement.lang !== "en";
const message = (ar, en) => isArabic() ? ar : en;

function setStatus(ar, en) {
  const status = byId("openModelStatus");
  if (status) status.textContent = message(ar, en);
}

function setProgress(info) {
  if (!info || typeof info !== "object") return;
  const file = typeof info.file === "string" ? info.file.split("/").pop() : "";
  const pct = Number.isFinite(info.progress) ? Math.max(0, Math.min(100, Math.round(info.progress))) : null;
  if (pct !== null) setStatus("تنزيل " + (file || "ملفات النموذج") + " — " + pct + "%", "Downloading " + (file || "model files") + " — " + pct + "%");
  else if (file) setStatus("جارٍ تجهيز " + file, "Preparing " + file);
}

async function loadLocalGenerator() {
  if (generator) return generator;
  if (generatorPromise) return generatorPromise;
  generatorPromise = (async () => {
    if (!window.isSecureContext) throw new Error("Safari requires HTTPS for local WebGPU inference.");
    if (!navigator.gpu || typeof navigator.gpu.requestAdapter !== "function") {
      throw new Error("WebGPU is unavailable in this Safari session. Update Safari/iOS or enable WebGPU support.");
    }
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error("Safari could not create a WebGPU adapter.");
    setStatus("جارٍ تحميل محرك التشغيل…", "Loading the inference runtime…");
    const { pipeline, env } = await import(TRANSFORMERS_URL);
    env.allowRemoteModels = true;
    env.useBrowserCache = true;
    setStatus("جارٍ تحميل Qwen2.5 (تنزيل أول مرة)…", "Loading Qwen2.5 (first-time download)…");
    generator = await pipeline("text-generation", MODEL_ID, {
      revision: MODEL_REVISION,
      device: "webgpu",
      dtype: "q4f16",
      progress_callback: setProgress
    });
    return generator;
  })().catch(error => {
    generatorPromise = null;
    throw error;
  });
  return generatorPromise;
}

function normalizeGeneratedText(output) {
  let value = Array.isArray(output) ? output[0]?.generated_text : output?.generated_text;
  if (Array.isArray(value)) {
    const last = value[value.length - 1];
    value = typeof last === "string" ? last : last?.content;
  }
  return typeof value === "string" ? value.trim() : "";
}

window.JON2_OPEN_MODEL_REQUESTED = false;
window.JON2_OPEN_MODEL_READY = false;
window.JON2_OPEN_MODEL = {
  async generate(history) {
    if (!generator) throw new Error("Local Qwen model is not loaded.");
    const safeHistory = (Array.isArray(history) ? history : [])
      .filter(item => item && (item.role === "user" || item.role === "assistant") && typeof item.content === "string")
      .slice(-6)
      .map(item => ({ role: item.role, content: item.content.slice(-420) }));
    if (!safeHistory.length || safeHistory[safeHistory.length - 1].role !== "user") {
      throw new Error("The latest conversation message is missing.");
    }
    const messages = [
      {
        role: "system",
        content: "أنت مساعد عربي مفيد وواضح. أجب باللغة العربية. إذا كتب المستخدم باللهجة المصرية فرد بالمصرية الطبيعية، وإذا كتب بالفصحى فرد بفصحى سهلة. افهم السؤال أولًا، وأجب مباشرة وبترابط، واشرح عند الحاجة بأمثلة قصيرة. لا تخترع حقائق أو مصادر؛ إذا لم تعرف فقل ذلك بوضوح. لا تكرر السؤال ولا تكرر الجمل. لا تدّع أنك نموذج Jon2؛ أنت Qwen2.5 يعمل محليًا داخل المتصفح."
      },
      ...safeHistory
    ];
    const output = await generator(messages, {
      max_new_tokens: 128,
      do_sample: true,
      temperature: 0.7,
      top_p: 0.88,
      repetition_penalty: 1.12,
      return_full_text: false
    });
    const answer = normalizeGeneratedText(output);
    if (!answer) throw new Error("The local model returned an empty answer.");
    return answer;
  }
};

const loadButton = byId("loadOpenModel");
if (loadButton) {
  loadButton.addEventListener("click", async () => {
    window.JON2_OPEN_MODEL_REQUESTED = true;
    window.JON2_OPEN_MODEL_READY = false;
    loadButton.disabled = true;
    setStatus("جارٍ فحص WebGPU وتحميل النموذج محليًا…", "Checking WebGPU and loading the local model…");
    try {
      await loadLocalGenerator();
      window.JON2_OPEN_MODEL_READY = true;
      setStatus("Qwen2.5 جاهز — رسائلك تُعالج محليًا على هذا الجهاز.", "Qwen2.5 is ready — your messages are processed locally on this device.");
      const mainStatus = byId("status");
      if (mainStatus) mainStatus.textContent = message("Qwen2.5 المحلي جاهز", "Local Qwen2.5 is ready");
      const note = byId("statusNote");
      if (note) note.textContent = message(
        "وضع Qwen المحلي نشط. الرسائل لا تُرسل إلى خادم محادثة أو API؛ التنزيل الأولي لملفات النموذج فقط من Hugging Face. هذا نموذج مؤقت وليس عقل Jon2 الأصلي.",
        "Local Qwen mode is active. Messages are not sent to a chat server or API; only the initial model files are downloaded from Hugging Face. This is a temporary model, not the original Jon2 brain."
      );
      const input = byId("input");
      if (input) input.placeholder = message("اكتب رسالتك إلى النموذج المحلي…", "Message the local model…");
    } catch (error) {
      window.JON2_OPEN_MODEL_READY = false;
      setStatus("فشل تشغيل النموذج المحلي: " + (error?.message || String(error)), "Could not start the local model: " + (error?.message || String(error)));
      console.error("Qwen local Safari initialization failed.", error);
    } finally {
      loadButton.disabled = false;
    }
  });
}
