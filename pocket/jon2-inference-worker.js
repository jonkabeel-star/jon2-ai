import { loadJon2SafariBundle } from "./jon2-safari-bundle.js";
import { validateJon2ArabicAnswer } from "./jon2-answer-quality.js";

let runtime = null;

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
      const answer = runtime.model.generate(runtime.tokenizer, message.prompt, message.maxTokens ?? 256);
      if (!validateJon2ArabicAnswer(answer)) {
        const error = new Error("JON2_QUALITY_REJECTED");
        error.code = "JON2_QUALITY_REJECTED";
        throw error;
      }
      self.postMessage({ type: "generated", requestId, answer });
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
