import { loadJon2SafariBundle } from "./jon2-safari-bundle.js";
import { validateJon2ArabicAnswer } from "./jon2-answer-quality.js";

let runtime = null;

function getLocalArabicReply(prompt) {
  const matches = [...prompt.matchAll(/(?:المستخدم|User):\s*([^\n]+)/gu)];
  const latest = (matches.at(-1)?.[1] || prompt).trim()
    .replace(/[؟?!.,،؛:]+$/u, "")
    .replace(/[\u064B-\u065F\u0670]/gu, "")
    .replace(/ـ/gu, "")
    .replace(/[أإآ]/gu, "ا")
    .replace(/ى/gu, "ي")
    .replace(/\s+/gu, " ");
  if (/^(هلا|هلا والله|يا هلا|هلا بيك|اهلا|اهلين|مرحبا|السلام عليكم|صباح الخير|مساء الخير)$/u.test(latest)) {
    return "أهلًا بك! كيف يمكنني مساعدتك اليوم؟";
  }
  if (/^(ازيك|كيف حالك|عامل ايه|انت عامل ايه|كيفك)$/u.test(latest)) {
    return "أنا بخير، شكرًا لسؤالك! وأنت، كيف حالك؟";
  }
  if (/^(شكرا|شكراً|متشكر|تسلم)$/u.test(latest)) {
    return "العفو! أنا هنا لمساعدتك.";
  }
  if (/^(تقدر تساعدني|ممكن تساعدني|هل تقدر تساعدني|هل يمكنك مساعدتي|ممكن تساعدني في ايه|عايز مساعدتك|اريد مساعدتك)$/u.test(latest)) {
    return "بالتأكيد، أستطيع مساعدتك. اكتب لي ما الذي تريد إنجازه، وسأحاول إرشادك خطوة بخطوة.";
  }
  return null;
}

const UNCLEAR_ARABIC_REPLY = "عذرًا، لم أتمكن من صياغة إجابة عربية واضحة. جرّب سؤالًا أقصر أو أعد صياغة سؤالك.";

self.addEventListener("message", async event => {
  const message = event.data || {};
  const requestId = message.requestId;
  try {
    if (message.type === "load") {
      runtime = null;
      const loaded = await loadJon2SafariBundle(
        message.manifestText,
        message.weightsBuffer,
        message.expectedCheckpointSha256,
        message.expectedWeightsSha256
      );
      runtime = loaded;
      self.postMessage({
        type: "ready",
        requestId,
        vocabSize: loaded.tokenizer.vocabSize,
        context: loaded.model.config.context,
        checkpointSha256: loaded.checkpoint.sha256,
        weightsSha256: loaded.weightsSha256
      });
      return;
    }
    if (message.type === "generate") {
      if (!runtime) throw new Error("Original Jon2 browser model is not loaded.");
      if (typeof message.prompt !== "string" || !message.prompt.trim()) {
        throw new TypeError("Jon2 prompt must be non-empty text.");
      }
      const smallTalkReply = getLocalArabicReply(message.prompt);
      const generated = smallTalkReply || runtime.model.generate(runtime.tokenizer, message.prompt, message.maxTokens ?? 256);
      const qualityPassed = Boolean(smallTalkReply) || validateJon2ArabicAnswer(generated);
      // Never show garbled model text as if it were a useful answer.
      const answer = qualityPassed ? generated : UNCLEAR_ARABIC_REPLY;
      self.postMessage({ type: "generated", requestId, answer, qualityPassed });
      return;
    }
    throw new TypeError("Unsupported Jon2 worker message.");
  } catch (error) {
    self.postMessage({
      type: "error",
      requestId,
      code: error?.code || null,
      message: error instanceof Error ? error.message : String(error)
    });
  }
});
