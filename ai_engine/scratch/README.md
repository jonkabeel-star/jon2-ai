# Jon2 AI — Original From-Scratch Foundation

This folder documents and verifies the independent model path.

## Non-negotiable design rules

- No GPT, Qwen, Llama, pretrained checkpoint, hosted AI API, or external inference service is used by this path.
- The model parameters are initialized randomly by PyTorch.
- The tokenizer is trained from the supplied project corpus; it is not downloaded.
- Training data must be original project text or content whose rights and license have been reviewed and approved.
- Do not commit private training corpora, personal conversations, or model checkpoints to the public repository.

## Current implementation

The initial model implementation lives in `ai_engine/jon2_core.py`:
- a causal Transformer language model written with PyTorch layers;
- a project-owned byte-level BPE tokenizer in `ai_engine/tokenizer.py`;
- a training pipeline in `ai_engine/train_jon2.py`.

The existing training entry point intentionally enforces a minimum corpus size. The currently recorded original dialogue set is far too small for a useful general-purpose language model. Do not lower that safeguard just to force a training run.

## Step 1 verification

From the repository root, run:

```bash
python ai_engine/scratch/verify_foundation.py
```

This checks that the model can be initialized from random weights, accepts token IDs, returns next-token logits, respects causal masking, and round-trips Arabic text through a tokenizer trained on a tiny in-memory sample. It does **not** claim that the model is trained or conversationally capable.

## Development sequence

1. Verify the random-initialized architecture.
2. Expand and review an original Arabic training corpus.
3. Train tokenizer and model on an appropriate GPU runtime.
4. Measure validation loss and held-out Arabic dialogue quality.
5. Save versioned checkpoints privately and test generation.
6. Only after reliable evaluation, connect this engine to the Jon2 website.

A from-scratch model starts with no learned language knowledge. It will produce poor output until it has been trained on a sufficiently large, high-quality corpus. A small prototype is a learning foundation, not a ChatGPT replacement.
