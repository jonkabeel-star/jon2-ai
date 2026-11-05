# Apertus 1.5 — source-level rights review

**Review date:** 2026-11-05  
**Decision: NOT APPROVED for Jon2. Do not download, fine-tune, or deploy.**

## Why the candidate fails Jon2's current data policy

The official Apertus team publishes a dataset catalogue and says it is the single source of truth for datasets used in each main training run. The catalogue includes dataset names, source URLs, license labels, versions, processing notes, and a `used_in` field.

Official sources:
- Release notes: https://huggingface.co/blog/swiss-ai/apertus-v15-release-notes
- Dataset catalogue: https://github.com/swiss-ai/apertus-data-transparency
- Raw catalogue snapshot: https://raw.githubusercontent.com/swiss-ai/apertus-data-transparency/main/Apertus%20dataset%20repository.tsv
- Apertus 1.5 model card: https://huggingface.co/swiss-ai/Apertus-v1.5-8B

### 1. Prohibited Wikipedia lineage

The official catalogue contains:

- `HuggingFaceFW/clean-wikipedia`
- license: `cc-by-sa-4.0`
- `used_in: v1`

Apertus 1.5 is explicitly continued pretraining from Apertus 1.0. Therefore the Apertus 1.5 weights inherit a base-model lineage trained in a run whose catalogue includes clean-Wikipedia. This conflicts with the owner's explicit instruction not to use Wikipedia-derived or CC BY-SA training material. This is sufficient by itself to reject the candidate for Jon2.

### 2. Other unresolved / incompatible records

The catalogue also contains v1.5 rows with labels such as `Unknown`, `Other`, `Mixed`, and `Openrail`, and at least one dataset row labelled `CC-BY-NC-4.0` (`ghananlpcommunity/ghana-english-speech-600hrs`, with a note that its license changed to NC in July 2026). Other records have complex subset filtering and mixed-license notes. Even where the project describes its process as using permissively licensed material, Jon2's stricter policy requires independently auditable source-level evidence and exclusions for every relevant training stage.

The published catalogue includes historical v1, v1.5, and later v2 rows. Do not mistakenly attribute v2-only rows to v1.5. The Wikipedia row is explicitly tagged v1, which matters because v1.5 continues pretraining from Apertus 1.0.

### 3. Model license does not cure data-policy mismatch

Apache-2.0 on the model weights does not override the owner's prohibition on Wikipedia / CC BY-SA source material or resolve uncertain third-party data rights.

## Decision

- **Apertus 1.5 8B: REJECTED for Jon2 under current policy.**
- **No weights downloaded.**
- **No Hub access policy accepted.**
- **No inference or fine-tuning enabled.**
- Do not silently waive the Wikipedia restriction or treat the model's Apache-2.0 weights license as a substitute for training-data clearance.

## Next engineering direction

Keep the existing Jon2 original model and its approved five-file corpus separate and unchanged. Continue searching for a model whose full training lineage is compatible with the owner's explicit data policy, or train a new Jon2 model only on individually reviewed, approved sources. A candidate must be checked across its full ancestry, not just the latest fine-tuning stage.
