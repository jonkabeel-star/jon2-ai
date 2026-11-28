# Jon2 Local Model Lab

An isolated, inference-only baseline experiment for evaluating the public open-weight model **Qwen/Qwen3-0.6B** on Modern Standard Arabic (MSA) and Egyptian Arabic.

## Safety boundary

- This lab lives only on `feat/jon2-local-model-lab`, created from `main`.
- It is not imported by `jon2_lite`, the public website, Cloudflare Worker, or `/api/chat`.
- `/api/chat` on `main` must remain HTTP 503 (`local_model_not_loaded`).
- No server, HTTP endpoint, public URL, tunnel, webhook, or external inference API is created.
- No model weights, datasets containing private user data, credentials, or runtime cache are committed.
- No training, fine-tuning, quantization, or merge/deploy is part of this baseline.
- The Colab notebook defaults to **all execution gates OFF**. Opening the notebook does not download or load a model.

## Model candidate and license review

- Repository: https://huggingface.co/Qwen/Qwen3-0.6B
- Model card currently declares **Apache-2.0**. Review the actual LICENSE file and applicable terms before downloading or using the weights; this note is not legal advice.
- Pinned Hugging Face revision: `c1899de289a04d12100db370d81485cdf75e47ca`.
- The model card describes support for 100+ languages and dialects, but this does not establish Egyptian Arabic quality. Egyptian performance must be measured by this lab.
- The model page currently reports approximately 1.52 GB of repository files and BF16 weights. Actual runtime memory also includes framework, activations, and KV cache; GPU availability is checked at runtime.

## Files

- `config/model_config.json`: immutable model identity, pinned revision, license review status, and execution gates.
- `notebooks/jon2_local_model_test.ipynb`: Colab notebook for a controlled baseline.
- `evaluation/*.jsonl`: 120 authored evaluation prompts, not training data.
- `evaluation/evaluation.py`: local runner and report writer.
- `reports/.gitkeep`: reports are generated at runtime and should not contain secrets or private data.

## Evaluation set

| Suite | Count |
|---|---:|
| MSA | 30 |
| Egyptian Arabic | 30 |
| Multi-step reasoning | 20 |
| Abstention / uncertainty | 20 |
| Safety / prompt-injection resistance | 20 |
| **Total** | **120** |

These are prompts with review criteria, not gold answers. Human review is required. Record factual correctness, language naturalness, dialect fit, hallucination, instruction following, and whether abstention was appropriate. Do not let the model grade itself.

This is an **inference-only test set**. If fine-tuning is ever proposed, create separate rights-reviewed training and validation corpora; keep this 120-question evaluation suite held out and do not train on it.

## Safe run order

1. Read the model card and LICENSE.
2. Inspect Colab GPU availability and available RAM without downloading the model.
3. Review the notebook and config. All three gates are initially false:
   - `ALLOW_PACKAGE_INSTALL`
   - `ALLOW_MODEL_DOWNLOAD`
   - `ALLOW_MODEL_LOAD`
4. Only after a separate explicit approval, enable the needed gate(s) in the notebook.
5. Download only from the pinned model revision; compute SHA-256 for every downloaded file and write a manifest to the Colab runtime.
6. Require `model.safetensors` to be exactly 1,503,300,328 bytes with SHA-256 `f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b` (the publisher-listed digest). A mismatch aborts before model loading.
7. Run a small smoke test first. Full evaluation remains separately gated.
8. Save results locally in the Colab session; do not upload generated outputs or model files to this repository.
9. Stop the Colab runtime after review.

## Reproducibility

The notebook records the model repository, pinned revision, Python / Transformers / PyTorch versions, device details, generation parameters, per-question latency, and file SHA-256 hashes. The computed hashes are evidence for the exact downloaded bytes; compare them across runs rather than trusting a mutable branch name.

## Explicit non-goals

No public deployment, no connection to Jon2 website/API, no modification of PR #187, no modification of `main`, no Worker edits, no persistent GPU hosting, no external inference provider, no automatic memory, and no claim that Qwen is a Jon2-owned original model.
