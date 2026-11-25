// Browser-side port of Jon2's original byte-BPE tokenizer.
// This is tokenizer parity groundwork only; it does NOT run the Transformer.
export class Jon2ByteBPETokenizer {
  constructor(merges) {
    if (!Array.isArray(merges)) throw new TypeError("Jon2 merges must be an array.");
    this.merges = merges.map((pair, rank) => {
      if (!Array.isArray(pair) || pair.length !== 2 ||
          !pair.every(x => Number.isInteger(x) && x >= 0 && x < 256 + rank)) {
        throw new TypeError("Invalid Jon2 BPE merge at token " + (256 + rank) + ".");
      }
      return [pair[0], pair[1]];
    });
    this.bytes = new Map();
    for (let i = 0; i < 256; i++) this.bytes.set(i, new Uint8Array([i]));
    this.encoder = new TextEncoder();
    this.decoder = new TextDecoder("utf-8", { fatal: false, ignoreBOM: true });
    this.pretokenize = /[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\p{L}\p{N}_]+|[^\p{L}\p{N}_\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/gu;
  }

  static fromDict(data) {
    if (!data || data.format !== "jon2-byte-bpe-v1" || data.base_vocab_size !== 256 ||
        !Array.isArray(data.merges)) {
      throw new TypeError("Unsupported Jon2 tokenizer format.");
    }
    return new Jon2ByteBPETokenizer(data.merges);
  }

  get vocabSize() { return 256 + this.merges.length; }

  encode(text) {
    if (typeof text !== "string") throw new TypeError("Tokenizer input must be text.");
    const result = [];
    for (const piece of text.match(this.pretokenize) || []) {
      let ids = Array.from(this.encoder.encode(piece));
      for (let rank = 0; rank < this.merges.length; rank++) {
        const [left, right] = this.merges[rank];
        const mergedId = 256 + rank;
        const next = [];
        for (let i = 0; i < ids.length;) {
          if (i + 1 < ids.length && ids[i] === left && ids[i + 1] === right) {
            next.push(mergedId);
            i += 2;
          } else {
            next.push(ids[i]);
            i += 1;
          }
        }
        ids = next;
      }
      result.push(...ids);
    }
    return result;
  }

  tokenBytes(tokenId, active = new Set()) {
    if (!Number.isInteger(tokenId) || tokenId < 0 || tokenId >= this.vocabSize) {
      throw new RangeError("Invalid Jon2 token id: " + tokenId);
    }
    if (this.bytes.has(tokenId)) return this.bytes.get(tokenId);
    if (active.has(tokenId)) throw new TypeError("Cyclic Jon2 tokenizer merge.");
    active.add(tokenId);
    const [left, right] = this.merges[tokenId - 256];
    const a = this.tokenBytes(left, active), b = this.tokenBytes(right, active);
    const joined = new Uint8Array(a.length + b.length);
    joined.set(a); joined.set(b, a.length);
    active.delete(tokenId);
    this.bytes.set(tokenId, joined);
    return joined;
  }

  decode(ids) {
    const chunks = Array.from(ids, id => this.tokenBytes(Number(id)));
    const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    return this.decoder.decode(bytes);
  }
}
