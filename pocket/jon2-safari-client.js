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
      this._settle(message.requestId);
      if (message.type === "error") pending.reject(new Error(message.message));
      else pending.resolve(message);
    });
    this.worker.addEventListener("error", event => {
      this._rejectAll(new Error("عقل Jon2 غير جاهز للرد"));
    });
    this.worker.addEventListener("messageerror", () => {
      this._rejectAll(new Error("عقل Jon2 غير جاهز للرد"));
    });
  }

  _settle(requestId) {
    const pending = this.pending.get(requestId);
    if (!pending) return null;
    clearTimeout(pending.timer);
    this.pending.delete(requestId);
    return pending;
  }

  _rejectAll(error) {
    for (const [requestId, pending] of this.pending) {
      this._settle(requestId);
      pending.reject(error);
    }
  }

  _request(type, payload, transfer = [], timeoutMs = 180000) {
    const requestId = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        const pending = this._settle(requestId);
        if (pending) pending.reject(new Error(
          "عقل Jon2 غير جاهز للرد"
        ));
      }, timeoutMs);
      this.pending.set(requestId, { resolve, reject, timer });
      try {
        this.worker.postMessage({ type, requestId, ...payload }, transfer);
      } catch (error) {
        const pending = this._settle(requestId);
        if (pending) pending.reject(error);
      }
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
    }, [weightsBuffer], 300000);
  }

  generate(prompt, maxTokens = 256) {
    return this._request("generate", { prompt, maxTokens }, [], 180000);
  }

  close() {
    this.worker.terminate();
    this._rejectAll(new Error("Jon2 Safari worker was closed."));
  }
}
