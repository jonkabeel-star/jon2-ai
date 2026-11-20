# Jon2 three-way dialogue training

This training mode connects the approved conversation splitter to the original Jon2 Transformer trainer. It does not use a hosted language model or pretrained weights.

## Required inputs

- A private dialogue source directory containing only the exact JSONL sources already listed in the split manifest, plus any other TXT/JSONL files required by the existing approval gate.
- A private `source_approvals.json` that records exact SHA-256, UTF-8 character count, reviewer, date, rights basis, intended use, and `APPROVED` status for every TXT/JSONL file selected by the approval gate.
- A prepared split directory created by `prepare_dialogue_splits.py`, outside the source directory. Its source hashes must still match the private source directory.

Do not put private source conversations, approval manifests, split files, checkpoints, or secrets in the public Git repository.

## Candidate-only training command

Run from a trusted private training runner after confirming that the data-size policy can be met:

```bash
PYTHONPATH=ai_engine python ai_engine/train_jon2.py \
  --data /private/jon2/approved-data \
  --approval-manifest /private/jon2/approved-data/source_approvals.json \
  --dialogue-splits-dir /private/jon2/prepared-splits \
  --candidate-only \
  --output /private/jon2/checkpoints/candidates/jon2-arabic-candidate.pt \
  --last-checkpoint /private/jon2/checkpoints/candidates/jon2-arabic-candidate-last.pt \
  --profile arabic_30m \
  --steps 10000
```

The trainer requires `--dialogue-splits-dir` and `--candidate-only` together. Both checkpoint paths must be inside a directory named `candidates`. This mode never writes to the normal release checkpoint paths.

## Data isolation rules

1. The source approval gate is rerun at training time.
2. Every JSONL source hash is checked against the split manifest. A changed or added source blocks training.
3. Train and validation partitions are hash-checked, parsed, and checked for normalized-message overlap.
4. The tokenizer BPE merges are learned from **train text only**.
5. Gradient updates and validation-based best-checkpoint selection use train and validation only.
6. The test partition file is read only as raw bytes for its recorded SHA-256. It is not decoded, parsed, tokenized, sampled, or passed to the model during training.
7. The checkpoint stores the split-manifest hash, all partition hashes, and explicit flags that test was not used.

## Release boundary

Every checkpoint from this mode is marked:

- `checkpoint_status = candidate_pending_arabic_quality_review`
- `arabic_quality_review_passed = false`
- `public_release_approved = false`

A lower validation loss is not proof of Arabic understanding. A separate final evaluator must load the candidate and use the untouched test partition once, after the training run is fixed. Then independent MSA and Egyptian Arabic semantic review is required. This PR does not add a release/approval mechanism and does not publish or deploy any checkpoint.

## Current readiness

This change wires the trainer to consume prepared splits. It does not approve existing dialogue files, create new training data, provision a GPU, or start training. The existing source approval, minimum one-million training-character, and minimum 20 training-tokens-per-parameter gates remain in force. If the approved training partition is too small, the trainer stops instead of duplicating data or lowering the thresholds.
