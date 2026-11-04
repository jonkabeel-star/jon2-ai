# Jon2 AI training data folder

Only UTF-8 text files with explicit source approval may be used for training. The training script reads local files; it does not fetch datasets from the internet.

## Current project-authored Arabic dialogue batches

| File | Purpose | Training status |
|---|---|---|
| original_dialogue_ar_batch_01.txt | Original Arabic dialogue batch 01 | Explicitly approved for the 2026-11-04 research-training run only |
| original_dialogue_ar_batch_02.txt | Original Arabic dialogue expansion batch 02 | Not yet approved for training |
| original_dialogue_ar_batch_03.txt | Original Arabic dialogue expansion batch 03 | Not yet approved for training |

The approval for batch 01 does not automatically extend to later batches, commercial use, or publication of model weights. The approval manifest must enumerate each training file and its exact SHA-256 and character count. The fail-closed approval gate must pass before training.

## Before adding or training another dataset

1. Record the exact source and date.
2. Confirm the source owner and rights to use it for machine-learning training.
3. Do not include private conversations, personal records, passwords, or confidential material.
4. Preserve applicable license and attribution requirements.
5. Deduplicate and quality-check text; do not inflate the corpus by repeating examples.
6. Keep evaluation questions separate from training data to measure generalization.

Project-authored text is not automatically a guarantee that every legal right is cleared. Record what was authored, by whom, and the permitted purpose.