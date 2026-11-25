import { Jon2TransformerCPU } from "./jon2-transformer.js";
import { Jon2ByteBPETokenizer } from "./jon2-tokenizer.js";

async function sha256Hex(buffer) {
  if (!globalThis.crypto?.subtle) throw new Error("WebCrypto SHA-256 is unavailable in this browser context.");
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

// Accepts manifest JSON text and the private binary weights file supplied by the owner.
// The original checkpoint fingerprint is pinned by the caller; no network model provider is used.
export async function loadJon2SafariBundle(manifestText, weightsBuffer, expectedCheckpointSha256, expectedWeightsSha256) {
  const manifest = typeof manifestText === "string" ? JSON.parse(manifestText) : manifestText;
  if (!manifest || manifest.format !== "jon2-safari-f32-v1" ||
      !manifest.checkpoint || !manifest.tensors || !Array.isArray(manifest.tensor_order)) {
    throw new TypeError("Unsupported Jon2 Safari bundle manifest.");
  }
  if (!/^[0-9a-f]{64}$/i.test(expectedCheckpointSha256 || "") ||
      manifest.checkpoint.sha256 !== expectedCheckpointSha256.toLowerCase()) {
    throw new Error("Jon2 original checkpoint fingerprint is not the approved pinned version.");
  }
  if (!(weightsBuffer instanceof ArrayBuffer)) throw new TypeError("Jon2 weights must be an ArrayBuffer.");
  if (!/^[0-9a-f]{64}$/i.test(expectedWeightsSha256 || "") ||
      manifest.weights_sha256 !== expectedWeightsSha256.toLowerCase()) {
    throw new Error("Jon2 Safari weights fingerprint is not the separately approved bundle hash.");
  }
  const actualWeightsSha = await sha256Hex(weightsBuffer);
  if (actualWeightsSha !== expectedWeightsSha256.toLowerCase()) throw new Error("Jon2 Safari weights SHA-256 mismatch.");
  if (manifest.byte_length !== weightsBuffer.byteLength) throw new Error("Jon2 Safari weights length mismatch.");

  const view = new DataView(weightsBuffer);
  const weights = {};
  const occupied = [];
  for (const name of manifest.tensor_order) {
    const item = manifest.tensors[name];
    if (!item || !Array.isArray(item.shape) || !Number.isInteger(item.offset) ||
        !Number.isInteger(item.elements) || item.offset < 0 || item.elements < 1) {
      throw new TypeError("Invalid Jon2 tensor manifest entry: " + name);
    }
    const expectedElements = item.shape.reduce((a, b) => {
      if (!Number.isInteger(b) || b < 1) throw new TypeError("Invalid tensor shape: " + name);
      return a * b;
    }, 1);
    if (expectedElements !== item.elements || item.offset + item.elements * 4 > weightsBuffer.byteLength) {
      throw new RangeError("Jon2 tensor bounds or shape mismatch: " + name);
    }
    occupied.push([item.offset, item.offset + item.elements * 4, name]);
    const values = new Float32Array(item.elements);
    for (let i = 0; i < item.elements; i++) values[i] = view.getFloat32(item.offset + i * 4, true);
    weights[name] = values;
  }
  occupied.sort((a,b)=>a[0]-b[0]);
  let cursor = 0;
  for (const [start,end,name] of occupied) {
    if (start !== cursor) throw new Error("Jon2 tensor binary has a gap or overlap before " + name);
    cursor = end;
  }
  if (cursor !== weightsBuffer.byteLength) throw new Error("Jon2 tensor binary contains unclaimed bytes.");
  const model = new Jon2TransformerCPU(manifest.config, weights);
  const tokenizer = Jon2ByteBPETokenizer.fromDict(manifest.tokenizer);
  if (tokenizer.vocabSize !== manifest.config.vocab_size) throw new Error("Jon2 tokenizer/model vocabulary mismatch.");
  return { model, tokenizer, checkpoint: manifest.checkpoint, weightsSha256: actualWeightsSha };
}
