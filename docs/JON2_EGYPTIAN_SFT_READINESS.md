# Jon2 Egyptian SFT readiness and data governance

## Current phase: inference quality only

The Qwen3.5-9B Kaggle run evaluates a public open-weight base model. It is not a Jon2-trained checkpoint. This work adds a Jon2 system prompt, bounded task-specific generation budgets, and completion metadata. No weights are changed.

## Release gates

Do not start fine-tuning or enable public chat until all gates below are reviewed and approved:

1. Keep the held-out benchmark isolated. Never copy it into training, validation, prompt examples, preference pairs, or synthetic-data generation.
2. For every training source, record source URL, publisher or creator, license name and version, license evidence, acquisition date, allowed uses, attribution requirements, and reviewer decision.
3. Remove personal data, secrets, copyrighted material without a suitable license, private conversations, and material with unclear provenance.
4. Deduplicate before splitting. Split by source, document, or conversation group, not adjacent random lines, to prevent leakage.
5. Keep a separately sealed validation set and final held-out test set. Do not tune prompts or hyperparameters against the final test set.
6. Have fluent Egyptian Arabic reviewers assess naturalness, factuality, safety, and dialect consistency.
7. Train only on a separate approved dataset artifact. Record dataset manifest hash, code commit, base-model revision, adapter hash, training configuration, and evaluation report.
8. Compare the adapter against the unmodified base model on the same held-out tests. Reject regressions in factuality, safety, instruction following, context retention, or completion rate.
9. Keep the base model and adapter separately versioned. Never overwrite original Jon2 checkpoints.
10. Require explicit owner approval before merging, deployment, or public release.

## Proposed future SFT format

Use JSONL records with messages arrays containing system, user, and assistant roles, plus metadata fields such as source_id, license_id, review_status, split, and conversation_group_id. Only records marked approved with a verified license may enter training.

## Proposed LoRA/DPO sequence

- First: supervised fine-tuning (SFT) with high-quality, rights-cleared Egyptian Arabic conversations.
- Then evaluate. Consider LoRA only if dataset size and hardware are sufficient and baseline comparison demonstrates a need.
- DPO is a later optional phase. It requires carefully human-reviewed chosen/rejected pairs and isolated evaluation. Never generate preference pairs from the held-out benchmark.
- Kaggle free GPU is temporary and quota-limited. Confirm memory, runtime, and storage feasibility before any training run. No permanent free hosting is assumed.

## Not authorized

This readiness plan does not authorize training, uploading private data, merging code, deployment, public chat release, or spending money.
