// CPU inference port of the original Jon2Transformer architecture.
// Requires an explicitly exported, fingerprint-verified weight bundle.
// No model weights are embedded in this source file.
const EPSILON = 1e-5;

function assertPositiveInteger(value, name) {
  if (!Number.isInteger(value) || value < 1) throw new TypeError(name + " must be a positive integer.");
}
function values(weights, name, length) {
  const value = weights[name];
  if (!value || value.length !== length) throw new TypeError("Missing or invalid Jon2 tensor: " + name);
  const out = Float64Array.from(value);
  for (const item of out) if (!Number.isFinite(item)) throw new TypeError("Non-finite Jon2 tensor value: " + name);
  return out;
}
function linear(input, rows, cols, weight, bias) {
  const output = new Float64Array(rows);
  for (let r = 0; r < rows; r++) {
    let sum = bias ? bias[r] : 0;
    const offset = r * cols;
    for (let c = 0; c < cols; c++) sum += weight[offset + c] * input[c];
    output[r] = sum;
  }
  return output;
}
function layerNorm(input, weight, bias) {
  const n = input.length;
  let mean = 0;
  for (let i = 0; i < n; i++) mean += input[i];
  mean /= n;
  let variance = 0;
  for (let i = 0; i < n; i++) {
    const delta = input[i] - mean;
    variance += delta * delta;
  }
  variance /= n;
  const scale = 1 / Math.sqrt(variance + EPSILON);
  const output = new Float64Array(n);
  for (let i = 0; i < n; i++) output[i] = (input[i] - mean) * scale * weight[i] + bias[i];
  return output;
}
// Abramowitz-Stegun erf approximation; maximum absolute error is about 1.5e-7.
function erf(x) {
  const sign = x < 0 ? -1 : 1;
  const a = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * a);
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
    - 0.284496736) * t + 0.254829592) * t * Math.exp(-a * a);
  return sign * y;
}
function gelu(x) {
  return 0.5 * x * (1 + erf(x / Math.SQRT2));
}

export class Jon2TransformerCPU {
  constructor(config, weights) {
    this.config = { ...config };
    const { vocab_size: vocab, width, heads, layers, context } = this.config;
    for (const [value, name] of [[vocab,"vocab_size"],[width,"width"],[heads,"heads"],[layers,"layers"],[context,"context"]]) {
      assertPositiveInteger(value, name);
    }
    if (width % heads !== 0) throw new TypeError("Jon2 width must be divisible by heads.");
    this.headWidth = width / heads;
    this.tokenEmbedding = values(weights, "token_embedding.weight", vocab * width);
    this.positionEmbedding = values(weights, "position_embedding.weight", context * width);
    this.finalNormWeight = values(weights, "final_norm.weight", width);
    this.finalNormBias = values(weights, "final_norm.bias", width);
    this.blocks = [];
    for (let layer = 0; layer < layers; layer++) {
      const prefix = "blocks.layers." + layer + ".";
      this.blocks.push({
        qkvWeight: values(weights, prefix + "self_attn.in_proj_weight", 3 * width * width),
        qkvBias: values(weights, prefix + "self_attn.in_proj_bias", 3 * width),
        attentionOutWeight: values(weights, prefix + "self_attn.out_proj.weight", width * width),
        attentionOutBias: values(weights, prefix + "self_attn.out_proj.bias", width),
        linear1Weight: values(weights, prefix + "linear1.weight", 4 * width * width),
        linear1Bias: values(weights, prefix + "linear1.bias", 4 * width),
        linear2Weight: values(weights, prefix + "linear2.weight", width * 4 * width),
        linear2Bias: values(weights, prefix + "linear2.bias", width),
        norm1Weight: values(weights, prefix + "norm1.weight", width),
        norm1Bias: values(weights, prefix + "norm1.bias", width),
        norm2Weight: values(weights, prefix + "norm2.weight", width),
        norm2Bias: values(weights, prefix + "norm2.bias", width)
      });
    }
  }

  forward(tokenIds) {
    if (!Array.isArray(tokenIds) || tokenIds.length === 0) throw new TypeError("Jon2 requires at least one input token.");
    const { vocab_size: vocab, width, context, heads } = this.config;
    let ids = tokenIds.map(Number);
    if (ids.some(id => !Number.isInteger(id) || id < 0 || id >= vocab)) throw new RangeError("Jon2 input contains an invalid token id.");
    if (ids.length > context) ids = ids.slice(-context);
    const length = ids.length;
    let hidden = ids.map((id, position) => {
      const row = new Float64Array(width);
      const tokenOffset = id * width, posOffset = position * width;
      for (let d = 0; d < width; d++) row[d] = this.tokenEmbedding[tokenOffset + d] + this.positionEmbedding[posOffset + d];
      return row;
    });

    for (const block of this.blocks) {
      const normalized = hidden.map(row => layerNorm(row, block.norm1Weight, block.norm1Bias));
      const qkv = normalized.map(row => linear(row, 3 * width, width, block.qkvWeight, block.qkvBias));
      const attended = [];
      for (let t = 0; t < length; t++) {
        const contextVector = new Float64Array(width);
        for (let h = 0; h < heads; h++) {
          const headOffset = h * this.headWidth;
          const scores = new Float64Array(t + 1);
          let maxScore = -Infinity;
          for (let j = 0; j <= t; j++) {
            let dot = 0;
            for (let d = 0; d < this.headWidth; d++) {
              dot += qkv[t][headOffset + d] * qkv[j][width + headOffset + d];
            }
            scores[j] = dot / Math.sqrt(this.headWidth);
            if (scores[j] > maxScore) maxScore = scores[j];
          }
          let denom = 0;
          for (let j = 0; j <= t; j++) { scores[j] = Math.exp(scores[j] - maxScore); denom += scores[j]; }
          for (let d = 0; d < this.headWidth; d++) {
            let sum = 0;
            for (let j = 0; j <= t; j++) sum += (scores[j] / denom) * qkv[j][2 * width + headOffset + d];
            contextVector[headOffset + d] = sum;
          }
        }
        const projected = linear(contextVector, width, width, block.attentionOutWeight, block.attentionOutBias);
        const row = new Float64Array(width);
        for (let d = 0; d < width; d++) row[d] = hidden[t][d] + projected[d];
        attended.push(row);
      }

      hidden = attended.map(row => {
        const normed = layerNorm(row, block.norm2Weight, block.norm2Bias);
        const expanded = linear(normed, 4 * width, width, block.linear1Weight, block.linear1Bias);
        for (let i = 0; i < expanded.length; i++) expanded[i] = gelu(expanded[i]);
        const contracted = linear(expanded, width, 4 * width, block.linear2Weight, block.linear2Bias);
        const result = new Float64Array(width);
        for (let d = 0; d < width; d++) result[d] = row[d] + contracted[d];
        return result;
      });
    }

    return hidden.map(row => {
      const normalized = layerNorm(row, this.finalNormWeight, this.finalNormBias);
      const logits = new Float64Array(vocab);
      // The original PyTorch model ties output.weight to token_embedding.weight.
      for (let token = 0; token < vocab; token++) {
        let sum = 0, offset = token * width;
        for (let d = 0; d < width; d++) sum += this.tokenEmbedding[offset + d] * normalized[d];
        logits[token] = sum;
      }
      return Array.from(logits);
    });
  }

  nextToken(tokenIds) {
    const rows = this.forward(tokenIds);
    const logits = rows[rows.length - 1];
    let best = 0;
    for (let i = 1; i < logits.length; i++) if (logits[i] > logits[best]) best = i;
    return { token_id: best, logits };
  }

  generate(tokenizer, prompt, maxTokens = 256, options = {}) {
    if (!tokenizer || typeof tokenizer.encode !== "function" ||
        typeof tokenizer.decode !== "function" || typeof tokenizer.tokenBytes !== "function") {
      throw new TypeError("Jon2 requires its native byte-BPE tokenizer.");
    }
    assertPositiveInteger(maxTokens, "maxTokens");
    if (maxTokens > 1024) throw new RangeError("Jon2 maxTokens cannot exceed 1024.");
    const promptIds = tokenizer.encode(prompt);
    if (!promptIds.length) throw new TypeError("Jon2 prompt produced no tokens.");

    // Match the safeguards used by the native PyTorch runtime.
    const repetitionPenalty = options.repetitionPenalty ?? 1.12;
    const noRepeatNgramSize = options.noRepeatNgramSize ?? 3;
    const temperature = options.temperature ?? 0.8;
    const doSample = options.doSample ?? true;
    const topK = options.topK ?? 40;
    if (!(temperature > 0) || repetitionPenalty < 1 || !Number.isInteger(noRepeatNgramSize) || noRepeatNgramSize < 0 || !Number.isInteger(topK) || topK < 0) {
      throw new TypeError("Invalid Jon2 generation options.");
    }
    const stopMarkers = ["\nالمستخدم:", "\nUser:"].map(value => new TextEncoder().encode(value));
    const allIds = promptIds.slice();
    const generatedIds = [];
    const promptBytes = joinBytes(promptIds.map(id => tokenizer.tokenBytes(id)));
    let generatedBytes = new Uint8Array(0);

    function joinBytes(chunks) {
      const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const output = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        output.set(chunk, offset);
        offset += chunk.length;
      }
      return output;
    }

    function findBytes(haystack, needle, from) {
      if (!needle.length) return from;
      outer: for (let i = from; i <= haystack.length - needle.length; i++) {
        for (let j = 0; j < needle.length; j++) {
          if (haystack[i + j] !== needle[j]) continue outer;
        }
        return i;
      }
      return -1;
    }

    function isValidUtf8Prefix(prefix, piece) {
      try {
        const decoder = new TextDecoder("utf-8", { fatal: true });
        decoder.decode(prefix, { stream: true });
        decoder.decode(piece, { stream: true });
        return true;
      } catch {
        return false;
      }
    }

    for (let step = 0; step < maxTokens; step++) {
      const logits = this.nextToken(allIds.slice(-this.config.context)).logits;
      const adjusted = Float64Array.from(logits);

      // Penalize tokens already emitted in this answer, not tokens in the prompt.
      if (repetitionPenalty > 1) {
        for (const tokenId of new Set(generatedIds)) {
          const value = adjusted[tokenId];
          adjusted[tokenId] = value >= 0 ? value / repetitionPenalty : value * repetitionPenalty;
        }
      }

      // Prevent repeating a trigram, matching ai_engine/jon2_core.py.
      if (noRepeatNgramSize > 0 && allIds.length >= noRepeatNgramSize - 1) {
        const prefixLength = noRepeatNgramSize - 1;
        const prefix = allIds.slice(-prefixLength);
        const banned = new Set();
        for (let i = 0; i <= allIds.length - noRepeatNgramSize; i++) {
          let matches = true;
          for (let j = 0; j < prefixLength; j++) {
            if (allIds[i + j] !== prefix[j]) { matches = false; break; }
          }
          if (matches) banned.add(allIds[i + prefixLength]);
        }
        for (const tokenId of banned) adjusted[tokenId] = -Infinity;
      }

      // Never append a byte sequence that would corrupt the UTF-8 answer.
      const validCandidates = [];
      const currentPrefix = joinBytes([promptBytes, generatedBytes]);
      for (let candidate = 0; candidate < adjusted.length; candidate++) {
        const score = adjusted[candidate];
        if (!Number.isFinite(score)) continue;
        const piece = tokenizer.tokenBytes(candidate);
        if (isValidUtf8Prefix(currentPrefix, piece)) validCandidates.push(candidate);
      }
      if (!validCandidates.length) break;

      // Match the native runtime: UTF-8 filtering first, then top-k, then
      // temperature-scaled sampling. Greedy mode remains available for parity tests.
      validCandidates.sort((a, b) => adjusted[b] - adjusted[a]);
      const candidates = doSample && topK > 0
        ? validCandidates.slice(0, topK)
        : validCandidates;
      let bestId;
      if (!doSample || candidates.length === 1) {
        bestId = candidates[0];
      } else {
        const maxLogit = adjusted[candidates[0]];
        const weights = candidates.map(id => Math.exp((adjusted[id] - maxLogit) / temperature));
        const total = weights.reduce((sum, weight) => sum + weight, 0);
        let draw = Math.random() * total;
        bestId = candidates[candidates.length - 1];
        for (let i = 0; i < candidates.length; i++) {
          draw -= weights[i];
          if (draw <= 0) { bestId = candidates[i]; break; }
        }
      }

      const selectedPiece = tokenizer.tokenBytes(bestId);
      allIds.push(bestId);
      generatedIds.push(bestId);
      generatedBytes = joinBytes([generatedBytes, selectedPiece]);

      // Stop only on a complete marker produced after the prompt.
      const completeStream = joinBytes([promptBytes, generatedBytes]);
      let stopAt = -1;
      for (const marker of stopMarkers) {
        const found = findBytes(completeStream, marker, promptBytes.length);
        if (found >= 0 && (stopAt < 0 || found < stopAt)) stopAt = found;
      }
      if (stopAt >= 0) {
        generatedBytes = generatedBytes.slice(0, stopAt - promptBytes.length);
        break;
      }
    }

    // Do not expose a dangling partial UTF-8 character at the token limit.
    while (generatedIds.length) {
      try {
        return new TextDecoder("utf-8", { fatal: true }).decode(generatedBytes).trim();
      } catch {
        const removed = generatedIds.pop();
        const removedBytes = tokenizer.tokenBytes(removed);
        generatedBytes = generatedBytes.slice(0, generatedBytes.length - removedBytes.length);
      }
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(generatedBytes).trim();
  }
}

// Deterministic tiny weights used only by the parity self-test; never production weights.
export function makeJon2ParityWeights(config) {
  const { vocab_size: vocab, width, context, layers } = config;
  const tensors = {};
  const definitions = {
    "token_embedding.weight": [vocab * width, 1, false],
    "position_embedding.weight": [context * width, 2, false],
    "final_norm.weight": [width, 15, true],
    "final_norm.bias": [width, 16, false]
  };
  for (let layer = 0; layer < layers; layer++) {
    const p = "blocks.layers." + layer + ".";
    const entries = [
      ["self_attn.in_proj_weight",3*width*width,3,false],
      ["self_attn.in_proj_bias",3*width,4,false],
      ["self_attn.out_proj.weight",width*width,5,false],
      ["self_attn.out_proj.bias",width,6,false],
      ["linear1.weight",4*width*width,7,false],
      ["linear1.bias",4*width,8,false],
      ["linear2.weight",width*4*width,9,false],
      ["linear2.bias",width,10,false],
      ["norm1.weight",width,11,true],
      ["norm1.bias",width,12,false],
      ["norm2.weight",width,13,true],
      ["norm2.bias",width,14,false]
    ];
    for (const [suffix,count,salt,isNorm] of entries) definitions[p+suffix]=[count,salt,isNorm];
  }
  for (const [name,[count,salt,isNorm]] of Object.entries(definitions)) {
    tensors[name] = Array.from({length:count},(_,i)=>{
      const value = (((i * 17 + salt * 13) % 97) - 48) / 200;
      return isNorm ? 1 + value * 0.1 : value;
    });
  }
  return tensors;
}
