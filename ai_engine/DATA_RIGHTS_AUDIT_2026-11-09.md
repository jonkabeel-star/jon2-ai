# Jon2 AI — Data Rights Audit (2026-11-09)

## Scope and outcome

This is a repository-level provenance audit, not a legal opinion. It distinguishes the current exact-file training approvals from new draft material and held-out evaluation prompts.

### Existing project-authored training files

The private source-approval manifest currently records six exact UTF-8 text files as approved for **private experimental research training only**:

- `original_dialogue_ar.txt`
- `original_dialogue_ar_batch_01.txt`
- `original_dialogue_ar_batch_02.txt`
- `original_dialogue_ar_batch_03.txt`
- `original_dialogue_ar_batch_04.txt`
- `original_seed_ar.txt`

Each record binds the approval to a SHA-256 fingerprint and exact character count. The approval basis is owner confirmation that the material is project-authored or authorized for private research. This gate verifies bytes and recorded approval metadata; it does not independently prove authorship or provide legal advice.

No third-party corpus, scraped text, Wikipedia/Wikimedia material, or external dataset is approved by this audit.

### Material explicitly excluded from training

- Three existing structured JSONL dialogue files under `training_data/dialogue/` are marked **not approved** in the training-data README.
- `data_drafts/egyptian_dialogue_draft_01.txt` is a new draft containing 80 user/assistant turns (14,328 characters). It is outside the trainer's default input directory and has no source-approval record. It must remain excluded until the owner reviews every example and approves the exact file fingerprint for a specified use.
- `evaluation/egyptian_arabic_prompts_draft.jsonl` contains 30 unique held-out prompts. It is an evaluation set, not training material. Keep it separate to prevent evaluation leakage.
- No new external data has been added or approved.

### Important repository visibility finding

The repository tree contains the source approval manifest and several training text files even though `.gitignore` says the approval manifest and private corpus files should not be committed. A `.gitignore` rule does not remove files already tracked in Git history. Therefore these files must be treated as publicly exposed in the repository's history, not as private storage.

Do not add further private data or credentials to this repository. Removing tracked files from the current tree would not erase prior public Git history. A history rewrite, cache/fork review, and any takedown or access-control actions require a separate owner-approved migration plan; no destructive history rewrite was performed here.

## Rights decision

| Material | Current decision | Permitted use |
|---|---|---|
| Six exact approved TXT files | Recorded owner approval; exact hashes checked by gate | Private experimental research only |
| Three existing training JSONL files | Not approved | None until reviewed |
| Egyptian dialogue draft 01 | Draft only; not approved | Human review only |
| Egyptian evaluation prompts | Held-out evaluation only | Never training |
| External/public web datasets | No source-level approval recorded here | None |

Public redistribution, commercial training, and public-model deployment are not covered by the existing private research approvals. Obtain separate, explicit rights approval before any such use.

## Required next actions

1. Review the exact six approved source files and confirm the recorded ownership/authorization basis remains accurate.
2. Review the 80 Egyptian dialogue turns for factuality, dialect naturalness, privacy, originality, and consistency.
3. If approved for private research, create a new private manifest record for the exact draft SHA-256 and character count. Do not edit the file after approval without re-review.
4. Keep all 30 evaluation prompts in the held-out evaluation directory and never copy them into training.
5. Before public or commercial training, obtain new permission explicitly covering that purpose.
