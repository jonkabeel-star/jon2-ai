# Jon2 training readiness — 2026-11-25

This is an operational status record, not approval to train, download gated data, modify the baseline checkpoint, or publish a model.

## 1. Data readiness

- The last recorded preflight for the existing approved-source corpus measured 193,519 probe tokens (193,403 in an earlier report) from 305,406 characters.
- The `arabic_30m` profile estimates 29,938,688 parameters at its target vocabulary.
- The current private GPU workflow enforces **20 measured corpus tokens per estimated parameter**, so the corresponding minimum is approximately **598,773,760 tokens**. An older training note describes a 10-token threshold (about 299,386,880 tokens); do not use that older number to bypass the current 20-token gate.
- Token requirements are a conservative project policy, not a universal law of language-model training. Passing them would still not prove Arabic quality.
- The research candidate registry now contains 17 candidates. All remain candidates/quarantined/evaluation-only as individually recorded. No candidate has been approved or downloaded by this change.
- Two newly recorded candidates:
  - `HeshamHaroon/asfar`: 123,062 MSA/classical Arabic page rows. The card says CC BY 4.0 covers its metadata/normalization and that underlying books are public domain; every book needs independent rights and attribution review. 78,049 rows are from filename-coded PDFs without recovered titles and must remain excluded until identified.
  - `Mo-Abdalkader/Egyptian-Arabic-English-Parallel-Corpus`: card declares CC BY 4.0 and reports SFT train/test plus DPO splits. It is task-specific Egyptian Arabic↔English parallel data, not a general dialogue corpus or monolingual pretraining corpus. Preserve the test split and verify exact revision, provenance, and attribution before use.
- Actual tokenizer counts must be measured after exact, approved files are ingested. Row counts, words, sentences, and page counts are not token counts.

## 2. GPU readiness

The private GPU workflow requires all of the following before it can start:
- a connected self-hosted Linux x64 GitHub Actions runner with labels `self-hosted`, `linux`, `x64`, and `jon2-gpu`;
- working NVIDIA driver, `nvidia-smi`, CUDA-enabled PyTorch, and sufficient GPU memory;
- private data and checkpoint directories outside the repository checkout;
- an exact, hash-pinned `source_approvals.json` that passes the current preflight.

No such connected runner has been verified. A GitHub-hosted CPU runner is not a CUDA substitute. No GPU training was dispatched.

## 3. Checkpoint storage and immutability

Known baseline checkpoint:
- file: `jon2-last.pt`
- SHA-256: `edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2`
- size: 3,471,600 bytes

Rules for any future candidate:
1. Never overwrite, rename, or delete the baseline.
2. Store candidates in a separate private location, proposed key prefix: `candidates/<github-run-id>/<run-attempt>/`.
3. Store the best and resumable checkpoints separately.
4. Write a manifest containing source commit, profile, training plan, approved data-manifest hash, corpus hash, tokenizer hash, checkpoint size, SHA-256, framework/CUDA/GPU versions, and timestamps.
5. Read each uploaded candidate back and verify its SHA-256 before treating the upload as successful.
6. Keep automatic evaluation reports separate from human semantic review. Candidate weights remain private and are never auto-promoted.
7. Promote only through a separately reviewed, explicit approval step.

The existing private Vercel Blob store is known to contain the baseline files. This record does not claim that a candidate prefix has been created or that a new checkpoint has been uploaded; the available connected storage actions do not expose a verified Blob upload/read-back workflow for this task.

## 4. Current decision

**STOP — not ready to train.** Data approvals and measured token volume are insufficient, and no qualifying free CUDA runner is verified. This is a fail-closed decision. Do not lower thresholds, use gated sources without authorization, invent or duplicate text, fall back to CPU for the 30M run, or alter the baseline checkpoint.
