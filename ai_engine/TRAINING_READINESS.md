# Jon2 AI — Training Readiness Gate

Last verified: 2026-11-04

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

A further test was added after that run to reject symlinks pointing outside the training-data directory. Its new workflow run must complete before this additional test is considered verified.

This CI checks Python syntax and the approval-gate policy only. It does not run model training, verify the real-world truth of rights claims, or prove model quality.

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
