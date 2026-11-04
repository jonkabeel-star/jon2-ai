# Jon2 AI — Training Readiness Gate

Last verified: 2026-11-04

## Latest dataset inventory and website API wiring (2026-11-04)

The privacy-conscious dataset inventory was added in commit `f472424c` and its Python CI run `41758598752` completed successfully:
- 5 repository-level approval-gate tests passed.
- 11 top-level engine/tokenizer/audit tests passed.
- 60 runtime, API, evaluation, training-resume, corpus-quality, and dataset-inventory tests passed.
- Total: 76 Python tests passed.
- The inventory found 2 text files, 15,673 UTF-8 characters, 27,843 bytes, 226 lines, 142 non-empty lines, and 9,786 tokens using a temporary 512-token BPE vocabulary.
- The approval gate reported BLOCKED because the private `source_approvals.json` manifest is absent. Training remains prohibited; no source was approved and no checkpoint was created.
- The inventory reports SHA-256 fingerprints and counts only; it does not copy corpus text into its report. Token counts are corpus-specific metrics, not a quality score.

The static website chat was then connected to a configurable FastAPI endpoint in commit `653b28b5`. It checks `/api/health`, posts user messages to `/api/chat`, displays backend errors without inventing model answers, and clearly reports that the backend is unavailable when no API URL is configured. The API base is supplied through `window.JON2_API_BASE_URL` before the page's main script. The GitHub Pages site still has no deployed FastAPI model host or trained checkpoint, so real chat remains unavailable.

A Node.js syntax check for the inline website JavaScript was added to GitHub Actions. Code-check run `41758974720` completed successfully on commit `7d94c580`.

These are engineering and integration improvements only. They do not establish a trained model, legal clearance, or production availability.


## Latest tokenizer audit and CI verification (2026-11-04)

The tokenizer-efficiency audit and its five regression tests were added. The Python workflow on commit \`a0c456fa\` completed successfully (run ID \`41757136544\`):
- 5 repository-level source-approval tests passed.
- 11 top-level AI-engine tokenizer/data-audit tests passed.
- 49 AI-engine runtime, evaluation, approval, resume, generation-stop, and coverage tests passed.
- Total: 65 Python tests passed across the three suites.
- Python compilation, structural data audit, Arabic coverage audit, and tokenizer audit all completed successfully.
- The tokenizer audit used a temporary 1,000-entry BPE vocabulary (256 byte tokens plus 744 learned merges) on the raw corpus text. It measured 15,674 characters, 27,844 UTF-8 bytes, and 7,835 tokens; 2,886 tokens (36.8347%) were byte fallback and 4,949 were learned merges. Exact decode round-trip passed.
- The separate Arabic sample had 36.8421% byte fallback; English and emoji/symbol samples had higher fallback rates (78.3784% and 76.9231%), while the mixed Arabic/English sample measured 30%. All sample round trips were exact. This indicates the current small corpus teaches more merges for some Arabic/mixed patterns than for English/emoji; it is not a language-quality score.
- The tokenizer audit reads raw text including whitespace and blank lines. The structural audit counts cleaned non-empty non-comment lines, so its 15,025-character total is a different metric, not a contradiction.
- Structural audit: zero exact normalized duplicate lines. It still warns that the cleaned corpus is below the 100,000-character reference.
- Code checks passed on commit \`854b32e5\`; the Python workflow for that documentation-only commit and the Pages deployment were still running when this note was prepared.

These results verify the tokenizer instrumentation and engineering tests only. They do not establish semantic understanding, approve the dataset, or create a trained checkpoint. The corpus remains small and rights review remains mandatory.


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

Added a separate 40-prompt Arabic evaluation set at `ai_engine/evaluation/prompts_ar.jsonl`. It covers basic explanation, follow-up ambiguity, arithmetic, summarization, creative writing, instruction following, uncertainty about live facts, logic, translation, beginner guidance, and phishing safety.

The set is JSONL, not .txt, so the current training corpus reader does not ingest it. The expanded set covers polysemy, negation, reference resolution, causal and temporal reasoning, morphology, idioms, metaphor, register, cohesion, inference, multi-turn context, counterfactuals, and uncertainty. The evaluation runner in `ai_engine/evaluate_model.py`:
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


### Training-default tokenizer configuration (2026-11-04)

The audit was aligned with the trainer's default BPE vocabulary size of 512. Python workflow run \`41757384408\` on commit \`23336d43\` completed successfully:
- All three Python suites passed again: 5 + 11 + 49 = 65 tests.
- The tokenizer audit used 512 vocabulary entries (256 byte tokens plus 256 learned merges) and measured 15,674 raw characters, 27,844 UTF-8 bytes, and 9,786 tokens.
- Byte fallback: 3,120 tokens (31.8823%); learned merges: 6,666; exact decode round-trip passed.
- Sample fallback rates: Arabic 25.0%, English 93.0233%, mixed Arabic/English 32.0%, emoji/symbols 81.4815%. All sample round trips passed.
- The high English and emoji fallback rates show that this Arabic-heavy training text does not teach compact merges for those domains. If English/emoji capability is desired, add diverse rights-cleared examples before training and measure again; do not change the ratios by artificial padding.

This is the more relevant tokenizer baseline for the current training defaults. It still does not indicate comprehension or model quality.


## Latest versioned dialogue-batch audit and CI repair (2026-11-04)

The versioned Arabic dialogue-batch audit fix and regression tests were completed in commits `96319a1b`, `2fe7c907`, `bba7b742`, and `e2210ec6`.

- The audit now recognizes versioned files whose stem begins with `original_dialogue_ar`, including `original_dialogue_ar_batch_01.txt`.
- The first test run exposed a Python `unittest` module-name collision because a new test file reused the existing top-level module name `test_audit_data`. The test file was renamed to `test_versioned_dialogue_batches.py`; no training text was changed.
- Final Python workflow run `41761026495` completed successfully: 5 source-approval tests, 11 top-level engine/tokenizer/audit tests, and 64 engine test-suite tests passed (80 total).
- GitHub Pages build `41761026684` completed successfully. Code-check runs for the final repair commit also completed successfully.
- Corpus quality audit: 3 text files, 151,748 source characters in the inventory, and 96,053 tokenizer tokens. The combined text audit reports 8 normalized duplicate-line groups and 17 excess duplicate lines, all in the 136,075-character dialogue expansion batch. The audit reports no email/phone privacy signals, no replacement characters, no unexpected control characters, and no zero-width/BOM characters for that batch. These are automated signals only; a human must still review the content.
- The exact-line duplicate result is not permission to delete or rewrite lines. The draft remains unchanged pending owner review.
- The inventory's approval gate remains `BLOCKED` because the private `source_approvals.json` manifest is absent. No dataset has been approved, no training has run, and no model checkpoint has been created by this workflow.

These results verify the code checks and corpus-audit tooling only. They do not establish semantic quality, legal clearance, or a trained assistant.
