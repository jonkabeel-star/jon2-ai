# Jon2 AI — Data, GPU Training, Evaluation and Release Pipeline

This document is an operational gate, not a claim that a dataset was downloaded or training ran.

## 1. Dataset rights policy (fail closed)

Every source must have its own immutable record before it can enter the training directory:
- exact upstream repository and revision/commit;
- original publisher and upstream source URLs for every component;
- exact licence text/version and a copy/hash of the terms;
- explicit evidence that the rights holder controls the underlying content, not merely the dataset wrapper;
- commercial model-training permission, redistribution obligations, attribution requirements, privacy/consent review;
- content language/dialect, collection date, row/document count, SHA-256 of each downloaded file;
- named reviewer, review date, intended use and signed approval.

A dataset card saying Apache/ODC/CC0 is not enough when it aggregates third-party web pages. Unknown provenance, conflicting licences, non-commercial terms, personal data without a lawful basis, or unclear commercial-training rights means quarantine only. Never override this by setting an environment variable or editing a status string.

### Research candidates — NOT APPROVED FOR COMMERCIAL TRAINING

| Candidate | Declared terms / scale | Decision |
|---|---|---|
| FineWeb2 Egyptian Arabic, Omartificial-Intelligence-Space | Card reports ~439M words / 1.4M documents and ODC-By 1.0; source is Common Crawl and its terms also apply | Quarantine pending source-level rights review and Common Crawl terms review |
| ArabicText-Large, Jr23xd23 | Card claims Apache-2.0, 244M words, 743,288 articles; upstream article provenance is not established by the card | Quarantine; no commercial approval |
| Alkhalil corpus (ACL 2026 paper) | Large MSA resource with a manually checked subset; commercial licence/rights need confirmation from authors/rightsholder | Contact authors; do not ingest yet |
| OpenITI | Underlying release is CC BY-NC-SA 4.0 | Excluded from commercial training |
| ArSyra dialect datasets | Preview access terms restrict use to research/evaluation; commercial licence requires contacting provider | Excluded until written commercial licence is obtained |

References:
- https://huggingface.co/datasets/Omartificial-Intelligence-Space/FineWeb2-Egyptian-Arabic
- https://huggingface.co/datasets/Jr23xd23/ArabicText-Large
- https://aclanthology.org/2026.abjadnlp-1.27/
- https://huggingface.co/datasets/ArSyra/arsyra-local-knowledge
- https://github.com/Bayanat-Labs/arabic-dataset-rights-index

The current repository-owned dialogue packs are approved only for private experimental research training under their existing manifest. They do not establish commercial-training rights and are far below the new minimum corpus threshold.

## 2. Ingestion and split isolation

1. Download each approved source into a separate quarantine directory; preserve the untouched archive and licence files.
2. Generate SHA-256 hashes and a per-file provenance manifest.
3. Deduplicate exact and near-duplicate documents before splitting.
4. Split by source document/group (not random lines) into train, validation and a sealed test set. Keep related versions, conversations and documents in one partition.
5. Store the sealed test set outside the training directory and never pass its path to the tokenizer, trainer, augmentation, prompt tuning or checkpoint selection.
6. Keep MSA and Egyptian-Arabic labels and report metrics separately.
7. The training preflight must pass the repository minimums: at least 1,000,000 approved Arabic characters and at least 20 training tokens per estimated model parameter. The test partition is not counted toward training tokens.

Do not copy test prompts into training data, synthetic instruction data, examples, logs used for training, or human feedback used for optimization.

## 3. GPU training (owner-controlled Colab/Kaggle runtime)

The GitHub Actions runner is CPU-only. Run training only in an attached GPU runtime where the user controls the private source files and credentials.

Before training:
```bash
nvidia-smi
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA GPU is required; training was not started."
print("GPU:", torch.cuda.get_device_name(0))
print("VRAM GiB:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))
print("PyTorch CUDA:", torch.version.cuda)
PY
```

Then run the repository's source-approval preflight against the approved data directory and manifest. Do not lower the minimums. Only after it reports ready, run the existing trainer with an explicitly selected Jon2 profile, an output checkpoint outside the source-data directory, validation enabled, and mixed precision where supported. Example command shape (replace paths only with the verified private data paths):

```bash
python ai_engine/preflight_training.py \
  --data /content/jon2-approved-data \
  --approval-manifest /content/jon2-approved-data/source_approvals.json \
  --profile arabic_30m \
  --output /content/jon2-checkpoints/jon2-arabic-30m.pt

python ai_engine/train_jon2.py \
  --data /content/jon2-approved-data \
  --approval-manifest /content/jon2-approved-data/source_approvals.json \
  --profile arabic_30m \
  --steps 10000 \
  --output /content/jon2-checkpoints/jon2-arabic-30m.pt \
  --last-checkpoint /content/jon2-checkpoints/jon2-arabic-30m-last.pt
```

After training, record GPU model/VRAM, CUDA and PyTorch versions, git commit, dataset manifest hash, tokenizer hash, seed, hyperparameters, start/end time, train/validation token counts, best validation loss, early-stop status, and checkpoint SHA-256. Keep checkpoints private; do not commit large weights to Git.

A profile selection is configuration only. It is not a trained model. A checkpoint is accepted only if its architecture and tokenizer metadata match the runtime and its hash is recorded.

## 4. Sealed evaluation

Use a separately maintained, never-trained-on held-out question set with unique IDs and document provenance. Include balanced MSA and Egyptian prompts across:
- comprehension and instruction following;
- factual accuracy (with independently verified answer keys);
- reasoning and multi-step tasks;
- summarization and paraphrasing;
- grammar, spelling, dialect naturalness and register;
- refusal/safety and uncertainty calibration.

Run inference deterministically first, save raw prompts/outputs and runtime metadata, and score separately by dialect. Automated checks may flag empty output, repetition, prompt leakage, script/language mismatch and malformed text; they cannot certify semantic quality. Human reviewers must independently rate factual accuracy, relevance, coherence, Arabic quality, instruction following and safety. Keep evaluator identities and review timestamp, conflicts, per-item ratings and adjudication notes.

No test prompt may be used for further training. If it is, retire that test set and create a new sealed set.

## 5. Human review and public release

A human reviewer must inspect the actual outputs from the exact checkpoint hash intended for deployment. Record the evaluation report and reviewer sign-off. A failed or incomplete review leaves the public gate closed.

Only after all conditions pass may the owner set all four deployment secrets/variables:
- `JON2_INFERENCE_TESTED=true`
- `JON2_QUALITY_REVIEW_PASSED=true`
- `JON2_CHAT_RELEASE_APPROVED=true`
- the production runtime must load the exact reviewed checkpoint hash.

These flags are release attestations, not substitutes for evidence. Never set them to make health look green. `JON2_EXPERIMENTAL_CHAT` never bypasses the public release gate.

## 6. Current status

As of this change: no newly rights-cleared large corpus has been approved or downloaded, no GPU training has been run by this workflow, no new checkpoint has been produced, no new held-out inference report or human sign-off exists, and public chat must remain closed.
