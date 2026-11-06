# Jon2 MoE training engine

**Status: training primitives implemented; no 20B training job has been launched.**

## Implemented
- Causal next-token language-model loss plus MoE router load-balancing auxiliary loss.
- One optimizer update with optional CUDA BF16 autocast, gradient clipping, and finite-value checks.
- Conservative 20B hardware admission gate: at least 8 visible CUDA GPUs, each with at least 80 GiB VRAM. This is a screening floor, not a fit guarantee.
- Corpus-scale gate: at least 10 approved tokens per trainable parameter. This is a project safety floor, not a quality guarantee.
- Atomic local checkpoint save and provenance-checked restore, including model/optimizer state, step, token count, config, corpus/tokenizer SHA-256, and RNG state.
- Optional PyTorch composable FSDP2 wrapping experts, transformer blocks, and root model.

## Safety
- Importing this module does not allocate a model or launch training.
- The default 20B model is not instantiated by tests.
- No workflow automatically starts large-model training.
- No data is fabricated, duplicated, or added to the approved corpus.
- Checkpoints are written locally only, never uploaded to a public repository.
- The explicit resume function uses weights_only=False only for trusted checkpoints produced by Jon2. Never load unknown checkpoint files.

## Still required
1. Real multi-GPU host satisfying the hardware gate, with tested FSDP2 and memory headroom.
2. Large, diverse, rights-approved Egyptian Arabic/MSA corpus. Existing approved Jon2 seed files do not pass the 10-token-per-parameter gate for 20B.
3. A separately trained/versioned tokenizer and SHA-256 fingerprint.
4. Distributed checkpoint coordination and a tested multi-node resume drill.
5. Throughput, held-out evaluation, and human review.

The iPhone-only setup does not satisfy these requirements. Do not call the target trained until a multi-GPU run produces a verified checkpoint and evaluation report.
