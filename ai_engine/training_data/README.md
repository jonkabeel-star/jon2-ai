# Jon2 AI training data folder

Only UTF-8 text files with explicit, exact-file source approval may be used for training. The training script reads local files; it does not fetch datasets from the internet.

## Current project-authored Arabic dialogue batches

| File | Purpose | Training status |
|---|---|---|
| original_dialogue_ar_batch_01.txt | Original Arabic dialogue batch 01 | **Not approved** — exact-file human review and private approval manifest required |
| original_dialogue_ar_batch_02.txt | Original Arabic dialogue expansion batch 02 | **Not approved** — exact-file human review and private approval manifest required |
| original_dialogue_ar_batch_03.txt | Original Arabic dialogue expansion batch 03 | **Not approved** — exact-file human review and private approval manifest required |

No batch currently has a recorded training approval. A request to create or expand project-authored examples is not a file-specific approval record for the exact bytes, rights basis, or intended deployment. Do not infer approval from a dataset-register entry, a passing automated audit, or the presence of a large character count.

Before any training run, the repository owner must review each exact file for factual accuracy, originality, privacy, quality, and intended use, then create the private `source_approvals.json` manifest with each file's SHA-256, exact Unicode character count, reviewer, review date, rights basis, and intended use. Keep that manifest out of the public repository. The fail-closed approval gate must pass before training.

## Before adding or training another dataset

1. Record the exact source and date.
2. Confirm the source owner and rights to use it for machine-learning training.
3. Do not include private conversations, personal records, passwords, or confidential material.
4. Preserve applicable license and attribution requirements.
5. Deduplicate and quality-check text; do not inflate the corpus by repeating examples.
6. Keep evaluation questions separate from training data to measure generalization.

Project-authored text is not automatically a guarantee that every legal right is cleared. Record what was authored, by whom, and the permitted purpose. No public or commercial training use is approved by this document.
