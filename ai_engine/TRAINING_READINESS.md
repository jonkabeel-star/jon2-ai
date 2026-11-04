# Jon2 AI — Training Readiness Gate

Last verified: 2026-11-04

## Latest safety, training-resume, and CI hardening (2026-11-04)

The latest full Python workflow #41755700669 completed successfully on commit `6e2c3a67`:
- All 5 repository-level source-approval tests passed.
- All 11 AI-engine tokenizer and data-audit tests passed.
- All 39 AI-engine API, runtime, evaluation, source-approval, legacy-training-gate, training-resume, and generation-stop tests passed.
- The workflow compiled Python modules, ran all three test suites, and completed the corpus audit successfully: 55 tests passed across the three suites.
- The API test suite verifies health/readiness reporting, successful mocked chat responses, missing-checkpoint HTTP 503 behavior, whitespace rejection, and the 2,000-character input limit.
- Combined Python/Node code-check runs #41755700787 and #41755700649 completed successfully.
- GitHub Pages build #41755700602 completed; deployment status was still finishing when this note was prepared.
- Dialogue generation stops before the next `المستخدم:` marker in both chat and held-out evaluation. Regression tests verify the evaluation runner passes the stop marker.
- Training checkpoints preserve model, optimizer, scheduler, AMP scaler, Python RNG, PyTorch RNG, CUDA RNG when present, training-plan metadata, corpus fingerprint, and the early-stopping no-improvement counter.
- Resume validation rejects changed corpus text, tokenizer/model settings, or training-plan settings instead of silently continuing a different run.
- Resume restores the scheduler's active learning rate into the optimizer, avoiding a warmup-rate reset after restart.
- Checkpoint writes are atomic and do not move the model between devices just to save a checkpoint.
- Every training approval is bound to the exact raw file bytes by a lowercase SHA-256 fingerprint and exact UTF-8 character count; the gate blocks changed files, missing fingerprints, and mismatched counts.
- The current corpus audit still reports 15,025 characters across 2 files, below the 100,000-character reference, with zero exact normalized duplicate lines. Rights still require human review.

These successful checks verify the engineering safeguards and site deployment. They do not create a trained checkpoint, approve any dataset, or establish assistant quality.

## Verified engineering tests

The Kaggle Bridge run #11 completed successfully (GitHub Actions run ID: 41749003450).

Verified from the Kaggle execution logs:
- The notebook was pushed and reached Kaggle status COMPLETE.
- The original Jon2 Transformer passed forward and backward passes.
- Arabic, Latin text, digits, and emoji passed a BPE encode/decode round trip.
- A BPE-configured model passed forward/backward.
- A temporary checkpoint was saved, loaded, and its tokenizer restored successfully.
- The data audit read both current original text files and found no exact normalized duplicate lines.

These are software and architecture tests only. They do not demonstrate useful language ability, factual knowledge, or assistant quality.

## Automated approval-gate CI

GitHub Actions code-check run #1 completed successfully (run ID: 41750071591):
- Python source compilation passed.
- All 9 source-approval unit tests passed.
- The approval gate accepted a complete exact-match test manifest and rejected missing, incomplete, duplicate, unapproved, and unsafe-path cases.

The follow-up run #41750323363 completed successfully:
- Python source compilation passed.
- All 10 approval-gate unit tests passed, including the symlink-outside-directory rejection test.

The tokenizer serialization defect was corrected in commit 5304dcca0204ceff7e2541ddbf431c52caf3a955. The subsequent full Python/code-check workflow on commit ae6b0bf0ea74ebd1f7ef01207cf8f94d7dcc9848 completed successfully:
- Python compilation passed.
- All 11 existing Python unit tests passed (including the tokenizer and audit test suites).
- JavaScript syntax and package-manifest checks passed.
- The separate approval-gate workflow passed all 10 tests.
- The dedicated Python workflow installed CPU PyTorch, compiled modules, passed all 5 approval-gate tests, and audited the current corpus.

The full Python workflow #41751132597 completed successfully on commit 4adbf0e3:
- All 11 AI-engine tests passed, including tokenizer serialization round-trip.
- All 4 new chat-runtime tests passed: missing checkpoints fail closed, checkpoint loading occurs once, empty prompts are rejected, and replies contain only generated completion text.
- The training approval tests, Python compilation, and data audit passed.
- The lightweight code-check workflow #41751195037 also passed after isolating PyTorch-dependent runtime tests from the no-PyTorch job.
- GitHub Pages build and deployment #41751193872 completed successfully.

These checks do not run model training, verify the real-world truth of rights claims, or prove model quality.

## Held-out Arabic evaluation pipeline

Added a separate 12-prompt Arabic evaluation set at `ai_engine/evaluation/prompts_ar.jsonl`. It covers basic explanation, follow-up ambiguity, arithmetic, summarization, creative writing, instruction following, uncertainty about live facts, logic, translation, beginner guidance, and phishing safety.

The set is JSONL, not .txt, so the current training corpus reader does not ingest it. The evaluation runner in `ai_engine/evaluate_model.py`:
- requires an existing trained checkpoint and refuses to generate random weights;
- generates one answer per held-out prompt;
- creates a structured review report with six blank human-scoring dimensions;
- never computes an automatic quality verdict or marks a release approved.

The rubric and tests were updated. The runner has not been executed against a real checkpoint because no trained checkpoint exists yet.

## Current compute observation

The verified Kaggle session reported:
- Python 3.13.18
- PyTorch 2.11.0+cpu
- RAM total approximately 31.35 GB
- CUDA available: False

The notebook metadata requests GPU, but the observed session did not provide CUDA. Do not plan a GPU training run until a fresh runtime explicitly reports CUDA and a GPU device.

## Current data inventory

The embedded project corpus contains:
- original_dialogue_ar.txt: 9,059 characters
- original_seed_ar.txt: 5,966 characters
- Total: 15,025 characters

This is a pipeline-test corpus, not a production dataset. The trainer's default minimum is 100,000 characters, but reaching that number alone does not establish adequate quality or coverage.

## Rights and approval gate

- The two small original files remain subject to owner review.
- ArabicText-Large remains NOT APPROVED because underlying source rights were not established.
- HPLT web-crawl remains NOT APPROVED for this project until underlying source rights and intended use are reviewed.
- The historical Arabic Wikipedia collection is not present in the current runtime and remains NOT APPROVED for training or commercial deployment pending a rights review and source-manifest verification.
- Never copy private conversations, secrets, or personal data into the training corpus.
- Do not use a source merely because its packaging or metadata declares an open licence; check rights in the underlying text.

## Next permitted engineering steps

1. Add a provenance manifest for each proposed source: source URL, exact licence/version, rights basis for underlying content, collection date, transformations, and intended use.
2. Review and approve each source before downloading or training.
3. Expand a diverse Arabic corpus using project-owned or clearly permitted material, with held-out evaluation examples kept separate.
4. Run a short CPU/GPU benchmark only after the actual runtime device is verified.
5. Train a small resumable experiment, retain best and last checkpoints, and evaluate answers manually using EVALUATION_RUBRIC.md.
6. Do not expose a checkpoint through the public chat API until it passes the release-blocking evaluation.

## Release status

NOT READY for assistant deployment. The original model code and checkpoint pipeline pass smoke tests, but no trained, evaluated production checkpoint exists.
