import { loadJon2SafariBundle } from "./jon2-safari-bundle.js";
import { validateJon2ArabicAnswer } from "./jon2-answer-quality.js";

let runtime = null;

export function requireUsableJon2Answer(answer) {
  if (typeof answer !== "string" || !answer.trim() || !validateJon2ArabicAnswer(answer)) {
    const error = new Error("عقل Jon2 غير جاهز للرد");
    error.code = "JON2_OUTPUT_REJECTED";
    throw error;
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
      if (!runtime) {
        const error = new Error("عقل Jon2 غير جاهز للرد");
        error.code = "JON2_MODEL_NOT_READY";
        throw error;
      }
      if (typeof message.prompt !== "string" || !message.prompt.trim()) {
        const error = new TypeError("عقل Jon2 غير جاهز للرد");
        error.code = "JON2_INVALID_PROMPT";
        throw error;
      }
      // Only the loaded original model generates an answer. Reject malformed,
      // empty, or repetitive output instead of exposing a fake/placeholder reply.
      let rawGenerated;
      try {
        rawGenerated = runtime.model.generate(
          runtime.tokenizer,
          message.prompt,
          message.maxTokens ?? 256
        );
      } catch (cause) {
        const error = new Error("عقل Jon2 غير جاهز للرد");
        error.code = "JON2_GENERATION_FAILED";
        error.cause = cause?.message || String(cause);
        throw error;
      }
      const answer = requireUsableJon2Answer(rawGenerated);
      self.postMessage({ type: "generated", requestId, answer, qualityPassed: true });
      return;
    }
    throw new TypeError("Unsupported Jon2 worker message.");
  } catch (error) {
    self.postMessage({
      type: "error",
      requestId,
      code: error?.code || (message.type === "load" ? "JON2_MODEL_LOAD_FAILED" : "JON2_INFERENCE_FAILED"),
      message: "عقل Jon2 غير جاهز للرد"
    });
  }
});
