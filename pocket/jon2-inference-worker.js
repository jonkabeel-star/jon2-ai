import { loadJon2SafariBundle } from "./jon2-safari-bundle.js";
import { validateJon2ArabicAnswer } from "./jon2-answer-quality.js";

let runtime = null;

export function requireUsableJon2Answer(answer) {
  if (typeof answer !== "string" || !answer.trim() || !validateJon2ArabicAnswer(answer)) {
    throw new Error("عقل Jon2 غير جاهز للرد");
  }
  return answer.trim();
}

if (typeof self !== "undefined") self.addEventListener("message", async event => {
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
      if (!runtime) throw new Error("عقل Jon2 غير جاهز للرد");
      if (typeof message.prompt !== "string" || !message.prompt.trim()) {
        throw new TypeError("عقل Jon2 غير جاهز للرد");
      }
      // Only the loaded original model generates an answer. Reject malformed,
      // empty, or repetitive output instead of exposing a fake/placeholder reply.
      const rawGenerated = runtime.model.generate(
        runtime.tokenizer,
        message.prompt,
        message.maxTokens ?? 256
      );
      const answer = requireUsableJon2Answer(rawGenerated);
      self.postMessage({ type: "generated", requestId, answer, qualityPassed: true });
      return;
    }
    throw new TypeError("Unsupported Jon2 worker message.");
  } catch (error) {
    self.postMessage({
      type: "error",
      requestId,
      code: error?.code || null,
      message: "عقل Jon2 غير جاهز للرد"
    });
  }
});
