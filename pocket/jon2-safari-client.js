// Safari module-worker client. Model files are read locally and transferred to the worker.
export class Jon2SafariClient {
  constructor(workerUrl = new URL("./jon2-inference-worker.js", import.meta.url)) {
    this.worker = new Worker(workerUrl, { type: "module" });
    this.nextId = 1;
    this.pending = new Map();
    this.worker.addEventListener("message", event => {
      const message = event.data || {};
      const pending = this.pending.get(message.requestId);
      if (!pending) return;
      this.pending.delete(message.requestId);
      if (message.type === "error") pending.reject(new Error(message.message));
      else pending.resolve(message);
    });
    this.worker.addEventListener("error", event => {
      const error = new Error(event.message || "Jon2 inference worker failed.");
      for (const pending of this.pending.values()) pending.reject(error);
      this.pending.clear();
    });
  }

  _request(type, payload, transfer = []) {
    const requestId = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(requestId, { resolve, reject });
      this.worker.postMessage({ type, requestId, ...payload }, transfer);
    });
  }

  async load(manifestFile, weightsFile, expectedCheckpointSha256, expectedWeightsSha256) {
    if (!(manifestFile instanceof Blob) || !(weightsFile instanceof Blob)) {
      throw new TypeError("Select the private manifest.json and weights.bin files first.");
    }
    const [manifestText, weightsBuffer] = await Promise.all([
      manifestFile.text(),
      weightsFile.arrayBuffer()
    ]);
    return this._request("load", {
      manifestText, weightsBuffer, expectedCheckpointSha256, expectedWeightsSha256
    }, [weightsBuffer]);
  }

  generate(prompt, maxTokens = 256) {
    return this._request("generate", { prompt, maxTokens });
  }

  close() {
    this.worker.terminate();
    const error = new Error("Jon2 Safari worker was closed.");
    for (const pending of this.pending.values()) pending.reject(error);
    this.pending.clear();
  }
}
