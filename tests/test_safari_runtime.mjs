import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { Jon2ByteBPETokenizer } from "../pocket/jon2-tokenizer.js";
import { Jon2TransformerCPU, makeJon2ParityWeights } from "../pocket/jon2-transformer.js";
import { validateJon2ArabicAnswer } from "../pocket/jon2-answer-quality.js";
import { requireUsableJon2Answer } from "../pocket/jon2-inference-worker.js";
import { buildJon2ConversationPrompt } from "../pocket/jon2-prompt.js";
import { JON2_SAFARI_GENERATION_OPTIONS, JON2_SAFARI_MAX_NEW_TOKENS } from "../pocket/jon2-inference-config.js";

const tokenizerFixtures = JSON.parse(await readFile(new URL("../pocket/tokenizer-parity-fixtures.json", import.meta.url), "utf8"));
const transformerFixture = JSON.parse(await readFile(new URL("../pocket/transformer-parity-fixture.json", import.meta.url), "utf8"));



test("Safari prompt builder matches the original Python conversation format", () => {
  const tokenizer = { encode: text => Array.from(text) };
  const history = [
    { role: "user", content: "قديم".repeat(40) },
    { role: "assistant", content: "رد سابق" },
    { role: "user", content: "سؤال سابق" },
    { role: "assistant", content: "إجابة سابقة" }
  ];
  const prompt = buildJon2ConversationPrompt("السؤال الحالي", history, tokenizer, 2000);
  const clipped = Array.from(history[0].content).slice(-90).join("");
  assert.equal(
    prompt,
    "المستخدم: " + clipped +
      "\nJon2: رد سابق" +
      "\nالمستخدم: سؤال سابق" +
      "\nJon2: إجابة سابقة" +
      "\nالمستخدم: السؤال الحالي\nJon2:"
  );
});

test("Safari prompt builder drops old turns and never truncates the current question", () => {
  const tokenizer = { encode: text => Array.from(text) };
  const history = [
    { role: "user", content: "أ".repeat(20) },
    { role: "assistant", content: "ب".repeat(20) },
    { role: "user", content: "ج".repeat(20) },
    { role: "assistant", content: "د".repeat(20) }
  ];
  const prompt = buildJon2ConversationPrompt("سؤال", history, tokenizer, 44);
  assert.ok(tokenizer.encode(prompt).length <= 43);
  assert.match(prompt, /المستخدم: سؤال\nJon2:$/);
  assert.throws(
    () => buildJon2ConversationPrompt("س".repeat(100), [], tokenizer, 20),
    /لن يتم اختصاره/
  );
});

test("Safari generation configuration matches the original Jon2 runtime", () => {
  assert.deepEqual(JON2_SAFARI_GENERATION_OPTIONS, {
    temperature: 1.0,
    repetitionPenalty: 1.10,
    noRepeatNgramSize: 3,
    topK: 0,
    doSample: false
  });
  assert.equal(JON2_SAFARI_MAX_NEW_TOKENS, 256);
});

test("Safari Arabic answer guard rejects the observed fragmented output", () => {
  const corrupted = "لا وأ ال ال الر ال ال الد الذي ال الذي ال الاست الطريقة ال ال الاسب الاسة ال الذي الذف ال ال ال الأو الذي الأو الاسة الاسب ال ال الذي الذي الأو الذي الاسم الأو الاسب ال ال ال ال ال ال ال ال ال ال ال ال ال الد الد الد ال الذي ال الد ال ال ال الد الاسة الذي الذي ال ال ال ال ال ال الد ال الذي الأو ال الد الد الأو الذي ال الد الذي الذي الد الد الد الد الد";
  assert.equal(validateJon2ArabicAnswer(corrupted), false);
  assert.equal(
    validateJon2ArabicAnswer("مرحباً، هذا رد من العقل الأصلي."),
    true
  );
});

test("Safari JavaScript tokenizer matches shared Python fixtures", () => {
  assert.equal(tokenizerFixtures.format, "jon2-tokenizer-parity-fixtures-v1");
  for (const fixture of tokenizerFixtures.cases) {
    const tokenizer = new Jon2ByteBPETokenizer(fixture.merges);
    assert.deepEqual(tokenizer.encode(fixture.text), fixture.expected, fixture.name);
    assert.equal(tokenizer.decode(fixture.expected), fixture.text, fixture.name + " decode");
  }
});

test("Safari tokenizer matches Python UTF-8 replacement and BOM behavior", () => {
  const tokenizer = new Jon2ByteBPETokenizer([]);
  assert.equal(tokenizer.decode([0xc3]), "�");
  assert.equal(tokenizer.decode([0xef, 0xbb, 0xbf, 65]), "\uFEFFA");
});

test("Safari tokenizer rejects invalid merge definitions", () => {
  assert.throws(() => new Jon2ByteBPETokenizer([[256, 256]]));
  assert.throws(() => Jon2ByteBPETokenizer.fromDict({
    format: "jon2-byte-bpe-v1", base_vocab_size: 256, merges: [[1, true]]
  }));
});

test("browser Transformer matches original PyTorch logits and greedy token", () => {
  const model = new Jon2TransformerCPU(
    transformerFixture.config,
    makeJon2ParityWeights(transformerFixture.config)
  );
  const result = model.nextToken(transformerFixture.tokens);
  for (const [tokenId, expected] of Object.entries(transformerFixture.expected_last_logits_selected)) {
    assert.ok(Math.abs(result.logits[Number(tokenId)] - expected) < 3e-5, "logit " + tokenId);
  }
  assert.equal(result.token_id, transformerFixture.expected_argmax);
  assert.ok(Math.abs(Math.max(...result.logits) - transformerFixture.expected_max_logit) < 3e-5);
});

test("browser Transformer truncates context, rejects invalid IDs, and generates greedily", () => {
  const model = new Jon2TransformerCPU(
    transformerFixture.config,
    makeJon2ParityWeights(transformerFixture.config)
  );
  assert.equal(model.forward([1,2,3,4,5,6,7,8,9]).length, 8);
  assert.throws(() => model.forward([999]));
  const tokenizer = {
    encode: () => [1,2],
    decode: ids => String.fromCharCode(...ids),
    tokenBytes: id => new Uint8Array([65 + (id % 26)])
  };
  assert.equal(model.generate(tokenizer, "prompt", 3).length, 3);
  assert.throws(() => model.generate(tokenizer, "prompt", 1025));
});

test("private Safari bundle loader verifies pinned hashes and tensor layout", async () => {
  const { webcrypto } = await import("node:crypto");
  if (!globalThis.crypto) globalThis.crypto = webcrypto;
  const { loadJon2SafariBundle } = await import("../pocket/jon2-safari-bundle.js");
  const config = transformerFixture.config;
  const weights = makeJon2ParityWeights(config);
  const shapes = {
    "token_embedding.weight": [config.vocab_size, config.width],
    "position_embedding.weight": [config.context, config.width],
    "final_norm.weight": [config.width],
    "final_norm.bias": [config.width]
  };
  const prefix = "blocks.layers.0.";
  Object.assign(shapes, {
    [prefix+"self_attn.in_proj_weight"]: [3*config.width,config.width],
    [prefix+"self_attn.in_proj_bias"]: [3*config.width],
    [prefix+"self_attn.out_proj.weight"]: [config.width,config.width],
    [prefix+"self_attn.out_proj.bias"]: [config.width],
    [prefix+"linear1.weight"]: [4*config.width,config.width],
    [prefix+"linear1.bias"]: [4*config.width],
    [prefix+"linear2.weight"]: [config.width,4*config.width],
    [prefix+"linear2.bias"]: [config.width],
    [prefix+"norm1.weight"]: [config.width],
    [prefix+"norm1.bias"]: [config.width],
    [prefix+"norm2.weight"]: [config.width],
    [prefix+"norm2.bias"]: [config.width]
  });
  const order = Object.keys(weights);
  const total = order.reduce((sum,name)=>sum+weights[name].length*4,0);
  const buffer = new ArrayBuffer(total), view = new DataView(buffer);
  const tensors = {};
  let offset = 0;
  for (const name of order) {
    const values = weights[name];
    tensors[name] = {offset,elements:values.length,shape:shapes[name]};
    values.forEach((value,index)=>view.setFloat32(offset+index*4,value,true));
    offset += values.length*4;
  }
  const digest = await webcrypto.subtle.digest("SHA-256",buffer);
  const weightsSha = Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
  const checkpointSha = "a".repeat(64);
  const manifest = {
    format:"jon2-safari-f32-v1",
    checkpoint:{size_bytes:3285607,sha256:checkpointSha},
    config,
    tokenizer:{format:"jon2-byte-bpe-v1",base_vocab_size:256,merges:[[104,105]]},
    byte_length:buffer.byteLength,
    weights_sha256:weightsSha,
    tensor_order:order,
    tensors
  };
  const loaded = await loadJon2SafariBundle(JSON.stringify(manifest),buffer,checkpointSha,weightsSha);
  assert.equal(loaded.tokenizer.vocabSize,config.vocab_size);
  assert.equal(loaded.model.nextToken([1,2,3,4]).token_id,transformerFixture.expected_argmax);
  await assert.rejects(
    loadJon2SafariBundle(JSON.stringify(manifest),buffer,checkpointSha,"b".repeat(64)),
    /fingerprint/
  );
  const corrupted = buffer.slice(0);
  new Uint8Array(corrupted)[0] ^= 1;
  await assert.rejects(
    loadJon2SafariBundle(JSON.stringify(manifest),corrupted,checkpointSha,weightsSha),
    /SHA-256 mismatch/
  );
});


test("Safari worker client resolves successful inference responses", async () => {
  const originalWorker = globalThis.Worker;
  class FakeWorker {
    listeners = new Map();
    addEventListener(type, callback) { this.listeners.set(type, callback); }
    postMessage(message) {
      queueMicrotask(() => this.listeners.get("message")?.({data:{
        type:"generated",requestId:message.requestId,answer:"أهلًا"
      }}));
    }
    terminate() {}
  }
  globalThis.Worker = FakeWorker;
  try {
    const { Jon2SafariClient } = await import("../pocket/jon2-safari-client.js?success-test");
    const client = new Jon2SafariClient();
    const history = [{role:"user",content:"سؤال سابق"}];
    const originalPostMessage = client.worker.postMessage.bind(client.worker);
    let sent;
    client.worker.postMessage = (message, transfer) => {
      sent = message;
      originalPostMessage(message, transfer);
    };
    const result = await client.generate("مرحبا", history, 8);
    assert.equal(sent.message, "مرحبا");
    assert.deepEqual(sent.history, history);
    assert.equal(sent.maxTokens, 8);
    assert.equal(result.answer, "أهلًا");
    client.close();
  } finally {
    globalThis.Worker = originalWorker;
  }
});

test("Safari worker client preserves stable internal failure codes", async () => {
  const originalWorker = globalThis.Worker;
  class FailingWorker {
    listeners = new Map();
    addEventListener(type, callback) { this.listeners.set(type, callback); }
    postMessage(message) {
      queueMicrotask(() => this.listeners.get("message")?.({data:{
        type:"error",requestId:message.requestId,code:"JON2_OUTPUT_REJECTED",
        message:"عقل Jon2 غير جاهز للرد"
      }}));
    }
    terminate() {}
  }
  globalThis.Worker = FailingWorker;
  try {
    const { Jon2SafariClient } = await import("../pocket/jon2-safari-client.js?diagnostic-code-test");
    const client = new Jon2SafariClient();
    await assert.rejects(client.generate("مرحبا", [], 8), error => {
      assert.equal(error.code, "JON2_OUTPUT_REJECTED");
      assert.match(error.message, /عقل Jon2 غير جاهز للرد/);
      return true;
    });
    client.close();
  } finally {
    globalThis.Worker = originalWorker;
  }
});

test("Safari worker client rejects timed-out generation instead of hanging chat", async () => {
  const originalWorker = globalThis.Worker;
  class SilentWorker {
    addEventListener() {}
    postMessage() {}
    terminate() {}
  }
  globalThis.Worker = SilentWorker;
  try {
    const { Jon2SafariClient } = await import("../pocket/jon2-safari-client.js?timeout-test");
    const client = new Jon2SafariClient();
    await assert.rejects(
      client._request("generate", {message:"مرحبا",history:[],maxTokens:8}, [], 5),
      /عقل Jon2 غير جاهز للرد/
    );
    assert.equal(client.pending.size, 0);
    client.close();
  } finally {
    globalThis.Worker = originalWorker;
  }
});

test("Safari worker client clears pending requests when closed", async () => {
  const originalWorker = globalThis.Worker;
  class SilentWorker {
    addEventListener() {}
    postMessage() {}
    terminate() {}
  }
  globalThis.Worker = SilentWorker;
  try {
    const { Jon2SafariClient } = await import("../pocket/jon2-safari-client.js?close-test");
    const client = new Jon2SafariClient();
    const pending = client._request("generate", {message:"مرحبا",history:[]}, [], 10000);
    client.close();
    await assert.rejects(pending, /worker was closed/);
    assert.equal(client.pending.size, 0);
  } finally {
    globalThis.Worker = originalWorker;
  }
});


test("Safari generation applies repetition penalty and blocks repeated trigrams", () => {
  const model = new Jon2TransformerCPU(
    transformerFixture.config,
    makeJon2ParityWeights(transformerFixture.config)
  );
  const logits = new Float64Array(transformerFixture.config.vocab_size);
  logits[88] = 10;
  logits[89] = 9;
  model.nextToken = () => ({logits});
  const tokenizer = {
    encode: () => [1,2],
    decode: ids => String.fromCharCode(...ids),
    tokenBytes: id => new Uint8Array([65 + (id % 26)])
  };
  assert.equal(model.generate(tokenizer, "prompt", 4, {doSample:false}), "KKKL");
});

test("Safari generation skips tokens that would corrupt UTF-8", () => {
  const model = new Jon2TransformerCPU(
    transformerFixture.config,
    makeJon2ParityWeights(transformerFixture.config)
  );
  const logits = new Float64Array(transformerFixture.config.vocab_size);
  logits[88] = 10;
  logits[89] = 9;
  model.nextToken = () => ({logits});
  const tokenizer = {
    encode: () => [1,2],
    decode: ids => String.fromCharCode(...ids),
    tokenBytes: id => new Uint8Array([id === 88 ? 0xff : 65 + (id % 26)])
  };
  assert.equal(model.generate(tokenizer, "prompt", 1, {doSample:false}), "L");
});

test("Safari worker never bypasses the original model with canned small-talk replies", async () => {
  const workerSource = await readFile(
    new URL("../pocket/jon2-inference-worker.js", import.meta.url),
    "utf8"
  );
  assert.doesNotMatch(workerSource, /function\s+getLocalArabicReply/);
  assert.match(workerSource, /buildJon2ConversationPrompt/);
  assert.match(workerSource, /JON2_SAFARI_GENERATION_OPTIONS/);
  assert.match(workerSource, /message\.maxTokens \?\? JON2_SAFARI_MAX_NEW_TOKENS/);
  assert.match(
    workerSource,
    /let rawGenerated;[\s\S]*?rawGenerated = runtime\.model\.generate\(/
  );
  assert.match(
    workerSource,
    /const answer = requireUsableJon2Answer\(rawGenerated\)/
  );
});

test("Public Safari chat keeps the unapproved native checkpoint out of answers", async () => {
  const page = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.doesNotMatch(page, /getJon2LocalIdentityReply|localIntentReply/);
  assert.doesNotMatch(page, /JON2_OPEN_MODEL|openModel-client|Qwen|Jais/i);
  assert.doesNotMatch(page, /experimentalAutoReply/);
  assert.doesNotMatch(page, /window.JON2_LOCAL_CLIENT.generate(normalizedValue, history)/);
  assert.ok(page.includes('addMessage(limitedPublicReply(value), "assistant")'));
  assert.ok(page.includes("quality review and human approval"));
  assert.doesNotMatch(page, /تعذر على النموذج المحلي توليد رد|The local model could not generate a reply/);
});

test("Public chat uses clear limited replies until native model approval", async () => {
  const page = await readFile(new URL("../index.html", import.meta.url), "utf8");
  assert.doesNotMatch(page, /experimentalAutoReply/);
  assert.ok(page.includes("function isJon2ReplyDisplayable(answer)"));
  assert.doesNotMatch(page, /Jon2 original-model reply failed the Arabic display-integrity check/);
  assert.doesNotMatch(page, /localQualityRejected/);
  assert.ok(page.includes('addMessage(limitedPublicReply(value), "assistant")'));
  assert.doesNotMatch(page, /window\.JON2_LOCAL_CLIENT\.generate\(normalizedValue, history\)/);
  assert.doesNotMatch(page, /JON2_OPEN_MODEL_REQUESTED|JON2_OPEN_MODEL_READY/);
});

test("Original Jon2 generation rejects empty output and quality-checks its own generated text", () => {
  assert.equal(
    requireUsableJon2Answer("مرحباً، هذا رد من العقل الأصلي."),
    "مرحباً، هذا رد من العقل الأصلي."
  );
  const fragmented = "لا وأ ال ال الر ال ال الد الذي ال الذي ال الاست";
  assert.equal(requireUsableJon2Answer(fragmented), fragmented);
  assert.equal(validateJon2ArabicAnswer(fragmented), false);
  assert.equal(
    validateJon2ArabicAnswer("مرحباً، هذا رد من العقل الأصلي."),
    true
  );
  assert.throws(
    () => requireUsableJon2Answer(""),
    /لم ينتج عقل Jon2 أي نص/
  );
});
