# Jon2 Arabic dialogue source audit — 2026-11-20

## Scope and method

This is a read-only structural and first-pass content audit of the three JSONL dialogue files currently listed in `ai_engine/training_data/README.md`. It does not grant source approval, certify legal rights, or replace a human factual/editorial review. The files remain excluded from training until their exact SHA-256 and UTF-8 character counts are added to the private approval manifest after owner review.

## Structural results

| File | Conversations | User turns | Assistant turns | Raw file characters |
|---|---:|---:|---:|---:|
| `dialogue/jon2_dialogue_expanded.jsonl` | 48 | 61 | 61 | 15,043 |
| `dialogue/jon2_dialogue_multiturn_stage2.jsonl` | 22 | 66 | 66 | 15,478 |
| `dialogue/jon2_dialogue_stage2.jsonl` | 117 | 117 | 117 | 27,870 |
| **Total** | **187** | **244** | **244** | **58,391** |

Parsed message-content characters (excluding JSON syntax and keys): approximately 40,198.

Checks performed:
- All 187 non-empty JSONL records parsed successfully.
- Every conversation had alternating user/assistant roles, non-empty string content, and an even number of messages.
- No malformed records, empty messages, or messages longer than 2,000 characters were found.
- 35 conversations contain more than one user/assistant exchange.
- No exact duplicate assistant messages were found.
- One repeated user prompt was found across two files: `ما الفرق بين الحقيقة والرأي؟`. Its two answers are similar but not identical; retain one canonical version or explicitly accept both as paraphrase variants.

## First-pass editorial observations

Positive patterns:
- Many answers appropriately state uncertainty for current exchange rates and avoid guessing.
- The medical example avoids diagnosis and directs severe or sudden symptoms to urgent care.
- Several examples teach source checking, evidence quality, privacy, and separation of train/validation/test data.
- The sampled Egyptian Arabic and Modern Standard Arabic phrasing is generally readable.

Items requiring owner/editor decision:
1. Resolve the duplicate `ما الفرق بين الحقيقة والرأي؟` prompt and decide whether to keep one canonical answer or both.
2. Review the complete JSONL files for factual accuracy, dialect consistency, repeated templates, and whether answers are sufficiently specific to teach useful behavior.
3. Confirm that no personal, confidential, or third-party copyrighted material is present.
4. Confirm the precise intended use: the existing TXT approval records authorize private experimental research training only, not public or commercial model training. Do not silently broaden that scope to the JSONL files.
5. Keep prompts about time-sensitive facts and medical topics under careful editorial review; the examples found in the first pass are cautious, but a structural scan is not a medical or financial fact check.

## Training-readiness blocker

The private `source_approvals.json` currently records six approved TXT sources only. It does not contain exact-file approval entries for these three JSONL files. Therefore the new three-way splitter/trainer approval gate must reject them until the owner reviews each exact file and updates the private manifest outside GitHub.

The six TXT approvals contain approximately 307,091 raw Unicode characters in total, based on their manifest character counts. The three JSONL files add approximately 40,198 message-content characters, not 58,391 training-text characters (the latter includes JSON formatting). Even if all three JSONL files were approved, the combined available text remains far below the project's 1,000,000-character minimum training gate and the separate minimum 20 training tokens per parameter. Do not start training, reduce the guard, or duplicate examples to force a run.

## Decision

**STRUCTURAL AUDIT: PASS. TRAINING APPROVAL: NOT GRANTED. TRAINING READINESS: FAIL / INSUFFICIENT DATA.**

Next steps:
1. Owner/editor reviews and resolves the duplicate prompt and all content concerns.
2. Owner explicitly approves the exact three JSONL files for private experimental research training only, if that is the intended scope.
3. Update the private approval manifest with exact SHA-256, UTF-8 character count, reviewer, date, rights basis, and intended use. Keep it out of the public repository.
4. Collect additional original or clearly licensed Arabic material with documented provenance; do not assume that the current small corpus can train a capable model from scratch.
5. Re-run the three-way split and training preflight only after the exact-file approval gate and data-volume requirements pass.

This report does not start training, modify model weights, publish a checkpoint, or deploy any service.
