# Jon2 Arabic 30M gated training

This workflow is a guarded path for training the original Jon2 Transformer from scratch with the `arabic_30m` architecture profile. Selecting the profile configures an estimated architecture; it is not a trained model.

## How to run

1. Run **Actions → Jon2 Arabic 30M — gated training → Run workflow** with `approve_training=false`. This performs the read-only source-rights and data-readiness preflight only.
2. Review the uploaded `jon2-arabic-30m-preflight-<run-id>` report. The report must say `readiness.ready: true`; every source must have an exact matching approval-manifest entry.
3. Only after reviewing that successful report, run the workflow again with `approve_training=true`. The training job still runs only if the new run's preflight succeeds.
4. The training job requires a repository-owned self-hosted Linux x64 runner labeled `gpu`, CUDA-enabled PyTorch, at least 8 GiB GPU memory, and the `KAGGLE_API_TOKEN` repository secret.
5. The private Kaggle dataset `jon2kabeel/jon2-private-model-checkpoint` must already exist and its privacy must be confirmed by the API. If any requirement is missing, the workflow fails closed before training.

## Safety guarantees

- No schedule, push, or pull-request trigger can start training.
- The approval input defaults to false. A successful preflight alone never starts training.
- The 30M trainer enforces exact source approvals, the 100,000-character floor, and 10 measured corpus tokens per instantiated parameter. These are project gates, not universal model-training laws.
- The new run starts from scratch. It does not load or overwrite legacy checkpoints.
- Best and resumable checkpoints use unique GitHub run IDs in their filenames, are SHA-256 fingerprinted, and are stored in a new private Kaggle dataset version. Existing versions are not deleted.
- GitHub Actions artifacts contain reports and logs only, never model weights, because this repository is public.
- Automatic numerical checks do not establish Arabic quality. A human must inspect generated Arabic before any public release.
- This workflow does not enable `JON2_CHAT_RELEASE_APPROVED` and does not publish a model or application.

## Current limitation

The most recent preflight observed only 193,403 probe tokens against an estimated 29,938,688-parameter architecture, so it was not ready. The configured 10-token-per-parameter gate corresponds to roughly 299 million tokens at that architecture size. The 80-turn Egyptian Arabic draft dataset remains unapproved and must not be used until its rights and content have been reviewed and its exact file hash is added to the approval manifest through the normal review process.

A free GitHub-hosted runner does not provide the required CUDA GPU. The training job intentionally waits for a suitable self-hosted GPU runner rather than silently falling back to slow CPU training.
