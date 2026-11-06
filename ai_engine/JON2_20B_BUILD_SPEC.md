# Jon2 20B — from-scratch model target and feasibility gate

**Status: ARCHITECTURE TARGET ONLY — NO 20B WEIGHTS HAVE BEEN CREATED**

## Decision

The project target is a project-owned Arabic-first language model with approximately 20 billion total parameters. It is not acceptable to claim that a parameter count, configuration file, random initialization, or empty checkpoint is a trained model.

The target must prioritize Egyptian Arabic, Modern Standard Arabic, instruction following, multi-turn consistency, factuality, and safe tool use.

## Model design direction

Use a decoder-only Transformer with sparse Mixture-of-Experts (MoE) feed-forward blocks, grouped-query attention, rotary position embeddings, RMSNorm, and a SwiGLU-style expert MLP. Sparse routing can reduce active computation per token, but all expert weights still need to be stored or streamed.

The design is informed by public modern MoE architectures, including OpenAI's published gpt-oss-20b architecture (21B-class total parameters, approximately 3.6B active per token, 24 layers, 32 experts with top-4 routing). This is an architecture reference only: Jon2 does not copy its weights, tokenizer, training corpus, or checkpoints.

## Implemented architecture code\n\n`ai_engine/moe_20b.py` now contains an experimental decoder-only MoE implementation with GQA, RoPE, RMSNorm, SwiGLU experts, top-k sparse routing, and a router load-balancing auxiliary loss. Its default configuration estimates approximately 20.61B total parameters and approximately 3.69B active parameters per token. Small configurations are unit-tested; the default 20B model is never instantiated by CI. This code creates randomly initialized parameters only when explicitly instantiated. It does not provide trained weights, tokenizer training, a distributed training runtime, or an inference service.\n\n`ai_engine/test_moe_20b.py` tests parameter estimates, routing, gradient flow, context limits, and tied embeddings using tiny test configurations.\n\n## Rights policy

- No third-party checkpoint is adopted by this specification.
- No pretrained model is downloaded.
- No model card or permissive software license is treated as proof that every training-data source has suitable rights.
- Do not train on Wikipedia, CC BY-SA, unknown web scrapes, or unapproved data.
- Every Jon2 training source must pass the repository's exact-hash source approval process before training.
- OpenAI gpt-oss-20b is not selected as Jon2's pretrained base in this phase: the public model documentation does not provide the source-by-source dataset provenance needed for Jon2's stricter data-rights policy.

## Storage and compute estimates

For a dense 20,000,000,000-parameter checkpoint, before tokenizer, metadata, runtime buffers, and KV cache:

| Representation | Approximate raw weight storage |
| --- | ---: |
| FP32 | 80 GB (74.5 GiB) |
| BF16 / FP16 | 40 GB (37.3 GiB) |
| 8-bit | 20 GB (18.6 GiB) |
| 4-bit | 10 GB (9.3 GiB) |

Real quantized files are larger because of scales, metadata, and packing. Sparse MoE does not remove the need to store the full parameter set.

Full-parameter training with Adam-style optimizer state can require hundreds of GB of memory across the distributed training system before activations, communication buffers, and checkpoint staging. A single iPhone 12 Pro Max cannot train or host this target. The phone remains the project-control device.

## Mandatory gates before real training

1. A rights-approved, diverse Arabic corpus with a held-out evaluation set.
2. An actual hardware inventory from the machine that will train the model.
3. A distributed-training plan with measured memory and throughput.
4. A reproducible tokenizer and model implementation with architecture tests.
5. A small-scale smoke test on the exact training stack.
6. A checkpoint written atomically with optimizer and RNG state.
7. Held-out Egyptian Arabic and MSA evaluation plus human review.
8. Release approval remains false until the evaluation is passed.

## Current reality

The current Jon2Transformer is a small dense educational model. Its training entry point does not implement MoE, distributed training, or a 20B architecture. The current approved corpus is far too small for a useful 20B model. The existing small checkpoint is not upgraded by changing dimensions; a 20B model would require a new architecture, tokenizer plan, large approved corpus, hardware, and a separate checkpoint lineage.

**No 20B training job is started by adding this document.**