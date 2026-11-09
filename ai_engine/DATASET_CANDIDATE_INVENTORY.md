# Arabic Dataset Candidate Inventory

Snapshot date: 2026-11-09  
Source: `ai_engine/DATA_RIGHTS_AUDIT_2026-11-09.md` on `main`  
Purpose: inventory only. This file does not create, expand, or imply any training approval.

## Current known materials

| Candidate | Current evidence | Current permitted scope | Action |
|---|---|---|---|
| `original_dialogue_ar.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| `original_dialogue_ar_batch_01.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| `original_dialogue_ar_batch_02.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| `original_dialogue_ar_batch_03.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| `original_dialogue_ar_batch_04.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| `original_seed_ar.txt` | Listed in the exact-file source approval records | Private experimental research training only | Reconfirm provenance/authorization and exact fingerprint before next run |
| Three JSONL dialogue files under `training_data/dialogue/` | Audit says explicitly not approved | None | Hold out of training pending individual review |
| `data_drafts/egyptian_dialogue_draft_01.txt` | 80 turns, 14,328 characters; draft without source-approval record | Human review only | Review every turn; if approved, bind approval to exact SHA-256 and stated use |
| `evaluation/egyptian_arabic_prompts_draft.jsonl` | 30 held-out prompts | Evaluation only | Keep isolated; never use for training |
| External/public datasets | No source-level approval recorded by the audit | None | Do not ingest until exact dataset license and intended-use review passes |

## Important visibility warning

The audit reports that the source approval manifest and several training text files are tracked in the public repository history, despite ignore rules. Treat those materials as publicly exposed. Do not add further corpus content, credentials, private notes, or raw datasets to this public repository. A history rewrite or takedown process is outside this inventory and requires a separate owner-approved plan.

## Immediate review order

1. Reconfirm the six exact-file approvals and their hashes from the authoritative private review records. The current scope remains private experimental research only.
2. Review the Egyptian 80-turn draft for originality, dialect naturalness, factuality, privacy, safety, and quality. No approval is implied.
3. Keep the 30 evaluation prompts separate and check that no near-duplicates leak into training.
4. Investigate each of the three unapproved JSONL files individually; do not approve them as a group without record-level evidence.
5. Only after evidence is available, create completed manifest rows. Unknown hashes, license terms, or rights must remain blank/unknown and the status must be `hold`.

## Scope boundary

This inventory does not approve commercial use, redistribution, public release, or any new training run. It does not alter model checkpoints, training workflows, or chat release settings.
