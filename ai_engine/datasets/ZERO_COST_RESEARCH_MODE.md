# Jon2 zero-cost research mode

**Financial constraint: zero spend.** This project mode must not create, start, reserve, or subscribe to paid compute, storage, data access, or APIs.

## Allowed work

- GitHub repository changes, source review, tests, static checks, and read-only preflight within the account's existing included allowances.
- CPU-only code tests on ordinary GitHub-hosted CI when the account's included Actions allowance permits them.
- Public datasets only after exact license, upstream provenance, privacy, and access terms are reviewed. A free download does not mean the content is legally reusable.
- Local, private evaluation of the original checkpoint without changing it, when a suitable free runtime and authorized private storage are available.

## Prohibited work

- Paid GPU providers, paid cloud instances, paid persistent volumes, paid dataset tiers, paid API inference, or paid subscriptions.
- Automatically accepting gated dataset terms, sharing account details, or buying a dataset.
- Starting a runner or compute host that can incur charges.
- Treating a provider's promotional credit, trial, or "free" listing as permission to spend or as a guaranteed permanent free GPU.
- Using Kaggle or Colab for this project.
- Uploading raw data, checkpoints, tokens, or private manifests to Git.

## GPU/training gate

The current training workflow requires a self-hosted Linux x64 runner with CUDA and label `jon2-gpu`. No such free runner has been verified. A GitHub-hosted CPU runner is not a substitute for that GPU runner. Therefore:
- do not dispatch the private GPU training workflow;
- do not provision a paid host;
- keep training blocked until a genuinely free GPU resource is actually available, verified, and permitted by its terms;
- if no such resource exists, continue with CPU CI, source/license review, data schemas, and evaluation design only.

## Checkpoint protection

- `jon2-last.pt` is the immutable baseline for this research track.
- Any candidate must be written to a separate private candidates directory and hashed.
- No candidate replaces the baseline automatically.
- No research-only source or checkpoint is approved for public/commercial release.

## Data readiness

The current preflight has already shown that the available corpus is far below the configured `arabic_30m` target. Do not lower the minimum tokens-per-parameter gate or inflate counts with duplicated/synthetic text. Keep training blocked until an approved, leakage-safe corpus genuinely meets the chosen profile's thresholds.

## Release gate

A passing code workflow, a successful model load, non-empty generated text, or a lower loss does not prove understanding. Public chat remains closed until held-out MSA/Egyptian tests, multi-turn context tests, safety/factuality checks, and documented human review pass.
