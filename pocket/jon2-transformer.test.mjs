import test from "node:test";
import assert from "node:assert/strict";
import { Jon2TransformerCPU } from "./jon2-transformer.js";

test("unigram no-repeat blocks prompt and previously generated tokens", () => {
  const model = Object.create(Jon2TransformerCPU.prototype);
  model.config = { context: 8 };
  model.nextToken = () => {
    const logits = Array(128).fill(-100);
    logits[65] = 10; // A: already present in prompt
    logits[66] = 9;  // B
    logits[67] = 8;  // C
    logits[68] = 7;  // D
    return { logits };
  };
  const tokenizer = {
    encode: () => [65],
    decode: ids => String.fromCharCode(...ids),
    tokenBytes: id => new Uint8Array([id])
  };

  const answer = model.generate(tokenizer, "A", 3, {
    doSample: false,
    noRepeatNgramSize: 1,
    repetitionPenalty: 1,
    topK: 0
  });

  assert.equal(answer, "BCD");
});


test("default Safari decoding is deterministic like the native Jon2 runtime", () => {
  const model = Object.create(Jon2TransformerCPU.prototype);
  model.config = { context: 8 };
  model.nextToken = () => ({ logits: [0, 1, 9, 8] });
  const tokenizer = {
    encode: () => [1],
    decode: ids => String.fromCharCode(...ids),
    tokenBytes: id => new Uint8Array([65 + id])
  };
  const originalRandom = Math.random;
  Math.random = () => { throw new Error("sampling must be disabled by default"); };
  try {
    assert.equal(model.generate(tokenizer, "prompt", 1), "C");
  } finally {
    Math.random = originalRandom;
  }
});
