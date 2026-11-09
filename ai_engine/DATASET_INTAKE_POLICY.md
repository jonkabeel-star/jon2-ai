# Arabic Dataset Intake, Rights, and Quality Gates

Status: policy and blank intake template only. This document does not approve any dataset.

## Purpose

This process governs candidate Arabic data before it can be used for Jon2 AI research, training, evaluation, or redistribution. A dataset is not approved merely because it is publicly accessible, downloadable, labeled "open", or hosted on a known platform.

## Non-negotiable rules

1. Keep raw corpora, model weights, credentials, personal data, and private review notes out of this public repository.
2. Record the exact source, version, retrieval date, license text or terms URL, and intended use for every candidate.
3. Review the license at the individual dataset and, where relevant, individual work/record level. Do not infer a license for an entire platform from one collection.
4. Do not use material with unclear provenance, missing terms, conflicting terms, or prohibited intended use.
5. Do not collect private messages, account data, access-controlled material, or personal/sensitive information. Reject or quarantine records that expose personal data.
6. Respect attribution, share-alike, non-commercial, no-derivatives, database rights, opt-out, and redistribution conditions. If commercial use is not explicitly permitted or legally clear, mark it as not approved for commercial use.
7. Keep evaluation/held-out examples separate from training data. Never train on the held-out evaluation set.
8. Preserve source snapshots and dataset hashes in private controlled storage where lawful; do not publish copyrighted source content or private notes in this repository.
9. A human reviewer must approve each candidate and each intended use. Approval for research does not imply approval for commercial use, redistribution, or public release.
10. No training starts unless the rights gate, quality gate, split-integrity gate, and model preflight all pass, followed by explicit human authorization for that training run.

## Candidate workflow

### A. Intake

Create one row per dataset/version in `data_manifest_template.csv`. Use a stable candidate ID. Do not put sample text, names, email addresses, or personal information in the manifest.

### B. Rights review

Verify and record:
- dataset owner/publisher and authoritative source URL;
- exact dataset name, version/revision, and retrieval date;
- license identifier and a direct URL to the applicable license/terms;
- whether the license permits research, model training, commercial use, modification, and redistribution;
- attribution, share-alike, notice, opt-out, and other obligations;
- whether individual records have different rights or provenance;
- whether source terms or law impose restrictions beyond the displayed license.

If any required fact is unknown, set rights status to `hold` or `rejected`, not `approved`.

### C. Privacy and safety review

Reject or quarantine content containing personal contact details, credentials, private conversations, sensitive personal data, or content collected from access-controlled spaces. Apply data minimization. Do not attempt to infer identity, demographics, or sensitive attributes from voice or text.

### D. Quality review

Assess:
- Arabic language and script quality;
- dialect labels and whether they are human-verified (do not infer dialect from script counts);
- encoding, malformed records, boilerplate, and language contamination;
- exact and near-duplicate rates;
- factual reliability and source quality where factual claims are present;
- toxic, abusive, unsafe, or otherwise unsuitable content;
- formatting and suitability for the intended training objective.

Record measurements and reviewer notes without copying protected text into the public repository.

### E. Split and leakage review

Create train/validation/test splits by source/document or another defensible grouping, not by randomly splitting near-duplicate fragments. Deduplicate before splitting. Keep test prompts and labels private and excluded from training. Record split hashes and confirm no overlap.

### F. Approval states

Use only these states:
- `candidate`: identified, not reviewed;
- `hold`: missing evidence or unresolved concern;
- `rejected`: rights, privacy, safety, or quality failure;
- `approved_research_only`: approved only for the specifically documented non-commercial research use;
- `approved_training`: rights and quality approved for the exact stated training purpose;
- `approved_commercial_training`: commercial training explicitly reviewed and approved;
- `expired`: approval withdrawn, terms changed, or source version superseded.

Approval is scoped to the exact dataset version, hash, and intended use. A new version requires a new review.

## Training release gate

Training remains disabled unless all of the following are true:
- every included dataset has an applicable approval state for the intended use;
- no included row is `candidate`, `hold`, `rejected`, or `expired`;
- privacy and safety checks pass;
- deduplication and split-integrity checks pass;
- the tokenizer-based token count and model preflight pass;
- a human reviewer signs the run-specific approval record;
- the user explicitly authorizes the specific training run.

Do not weaken readiness thresholds merely to make a run pass. If data volume is insufficient, report the shortfall and revise the data/model plan rather than bypassing the gate.

## Current project caution

The previous read-only preflight for the `arabic_30m` profile reported approximately 193,403 tokens and failed the project's configured tokens-per-parameter readiness gate. This is a project-specific policy result, not a universal scientific rule. No 30M training is authorized by this document.

## Change control

This policy and blank template are documentation only. They do not change training workflows, approve existing corpora, modify checkpoints, enable chat release, or authorize publication. Review proposed changes through a pull request before merging to `main`.
