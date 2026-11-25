# Jon2 private GPU runner — zero-cost mode

**No paid compute or storage is authorized.** Do not create a cloud GPU instance, Pod, persistent volume, subscription, paid trial, or paid API account. The project is in zero-spend mode.

## Current status

- No free, always-available NVIDIA GPU host has been verified.
- The GitHub Actions training workflow requires a self-hosted Linux x64 runner labelled `jon2-gpu` with CUDA.
- GitHub-hosted CPU runners cannot satisfy that GPU requirement.
- Therefore training is blocked until a genuinely free GPU resource is available and its terms are checked.
- Do not dispatch the GPU training workflow and do not provision a paid host.

## If a genuinely free GPU host becomes available

Only after verifying that it is actually free (not a trial, credit, or paid storage add-on), its privacy/isolation terms, and its usage limits, the host would need:
- Linux x64;
- NVIDIA driver and CUDA-enabled PyTorch;
- a private persistent data/checkpoint location;
- a repository-scoped GitHub Actions runner with labels `self-hosted`, `linux`, `x64`, and `jon2-gpu`.

No runner token, data, checkpoint, or private approval manifest may be committed to Git or pasted into chat. Never run untrusted fork code on a private runner.

## Private storage layout (design only)

If a no-cost host with private persistent storage is verified, keep data and checkpoints outside the repository checkout:
- `<private-data-dir>` — raw/normalized approved corpus and private source approval manifest;
- `<private-checkpoint-dir>` — splits, reports, and candidate checkpoints;
- `<private-checkpoint-dir>/candidates` — candidate-only model weights.

The current bootstrap scripts validate a host; they do not provision one, download data, or start training.

## Data and checkpoint safeguards

- The source registry is a candidate list, not permission to download or train.
- Review exact license, upstream provenance, privacy, access conditions, and immutable revision before intake.
- Keep official test/evaluation partitions separate from training.
- Keep all raw data and private manifests out of Git.
- Preserve the original `jon2-last.pt`; all new checkpoints must be separate candidates and hashed.

## Stop condition

If no verified free GPU host and private storage exist, continue only with source review, CPU-based tests, evaluation design, and read-only preflight. Never lower data thresholds, duplicate text to inflate counts, or claim that CPU CI is model training.

See `ai_engine/datasets/ZERO_COST_RESEARCH_MODE.md`.
