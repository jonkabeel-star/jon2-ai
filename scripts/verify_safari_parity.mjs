#!/usr/bin/env node
// Compare a private Safari bundle against logits exported from the exact same
// original PyTorch checkpoint. Keep manifest, weights, and reference private.
import { readFile } from "node:fs/promises";
import { webcrypto } from "node:crypto";
import { loadJon2SafariBundle } from "../pocket/jon2-safari-bundle.js";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

function arg(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}
const manifestPath = arg("--manifest");
const weightsPath = arg("--weights");
const referencePath = arg("--reference");
if (!manifestPath || !weightsPath || !referencePath) {
  console.error("Usage: node scripts/verify_safari_parity.mjs --manifest manifest.json --weights weights.bin --reference python-reference.json");
  process.exit(2);
}

const [manifestText, weightsBuffer, referenceText] = await Promise.all([
  readFile(manifestPath, "utf8"),
  readFile(weightsPath),
  readFile(referencePath, "utf8")
]);
const manifest = JSON.parse(manifestText);
const reference = JSON.parse(referenceText);
if (reference.format !== "jon2-python-safari-parity-reference-v1") {
  throw new Error("Unsupported Python reference format.");
}
if (reference.checkpoint_sha256 !== manifest.checkpoint?.sha256 ||
    reference.weights_sha256 !== manifest.weights_sha256) {
  throw new Error("STOP: Python reference and Safari bundle do not identify the same checkpoint/weights.");
}

const loaded = await loadJon2SafariBundle(
  manifestText,
  weightsBuffer.buffer.slice(weightsBuffer.byteOffset, weightsBuffer.byteOffset + weightsBuffer.byteLength),
  manifest.checkpoint.sha256,
  manifest.weights_sha256
);
const reports = [];
let failed = false;
for (const item of reference.prompts) {
  const jsIds = loaded.tokenizer.encode(item.prompt);
  const idsMatch = JSON.stringify(jsIds) === JSON.stringify(item.token_ids);
  const bounded = jsIds.slice(-loaded.model.config.context);
  const jsLogits = loaded.model.forward(bounded).at(-1);
  let maxAbsError = 0;
  let squaredError = 0;
  for (let i = 0; i < jsLogits.length; i++) {
    const delta = jsLogits[i] - item.python_logits[i];
    maxAbsError = Math.max(maxAbsError, Math.abs(delta));
    squaredError += delta * delta;
  }
  const rmsError = Math.sqrt(squaredError / jsLogits.length);
  const jsArgmax = jsLogits.reduce((best, value, index) => value > jsLogits[best] ? index : best, 0);
  const argmaxMatch = jsArgmax === item.python_argmax;
  // JS uses Float64 accumulation while PyTorch uses FP32; permit small
  // rounding differences but require the greedy next-token decision to match.
  const logitsMatch = maxAbsError <= 0.002 && rmsError <= 0.0005;
  const passed = idsMatch && argmaxMatch && logitsMatch;
  failed ||= !passed;
  reports.push({
    prompt: item.prompt,
    tokenCount: jsIds.length,
    tokenIdsMatch: idsMatch,
    pythonArgmax: item.python_argmax,
    safariArgmax: jsArgmax,
    argmaxMatch,
    maxAbsLogitError: Number(maxAbsError.toExponential(4)),
    rmsLogitError: Number(rmsError.toExponential(4)),
    logitsWithinTolerance: logitsMatch,
    passed
  });
}
console.log(JSON.stringify({
  format: "jon2-safari-parity-report-v1",
  checkpointSha256: manifest.checkpoint.sha256,
  weightsSha256: manifest.weights_sha256,
  promptCount: reports.length,
  passed: !failed,
  reports
}, null, 2));
if (failed) process.exit(1);
