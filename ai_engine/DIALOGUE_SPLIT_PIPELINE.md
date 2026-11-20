# Jon2 approved three-way dialogue preparation

This command prepares leakage-resistant partitions from structured JSONL conversations. It is a data-preparation step only: it does not train weights, approve a dataset, change the model, or deploy the API.

## Run after reviewing and approving every exact source

Keep the approval manifest private and outside the public repository. The manifest must contain an exact SHA-256, UTF-8 character count, reviewer, date, rights basis, intended use, and `APPROVED` status for every selected `.txt` and `.jsonl` file in the data directory.

```bash
python ai_engine/prepare_dialogue_splits.py \
  --data ai_engine/training_data \
  --approval-manifest /private/path/source_approvals.json \
  --output /private/path/jon2-dialogue-splits \
  --validation-fraction 0.1 \
  --test-fraction 0.1 \
  --seed 42
```

The output directory must be outside the source directory. The command fails closed if any selected source is missing from the manifest, has changed since approval, contains malformed conversations, or shares normalized message text across independent partitions.

## Output

- `train.jsonl`: candidate training partition.
- `validation.jsonl`: candidate validation partition for checkpoint selection.
- `test.jsonl`: untouched held-out partition. Never train on it, fit tokenizer merges on it, or use it to choose a checkpoint.
- `split_manifest.json`: source and output hashes, conversation counts, split algorithm, seed, and explicit non-training status.

Conversations are assigned as whole units. If any normalized user or assistant message is shared between conversations, those conversations are linked and kept in the same partition. This is stricter than splitting individual message pairs.

## Current limitation — do not skip this

The existing `train_jon2.py` entry point still uses its established source-file train/validation split. This new preparation command does **not** silently change that trainer or automatically consume these three output files. A separate trainer-integration change must map train and validation partitions into training while reserving test for final evaluation. Until that integration and its tests exist, treat these files as audited split artifacts only and do not claim a three-way training run has happened.

The three existing project dialogue JSONL files remain unapproved unless the owner reviews the exact file contents and records their exact fingerprints and rights basis in the private approval manifest. This command cannot grant that approval.
