# Jon2 quality roadmap — staged execution

## Existing project assets found during review
- The repository already has a private experimental source-approval manifest covering six project-authored text files. Those approvals are limited to private research training; they do not authorize public or commercial use.
- Existing training-data documentation marks three structured dialogue JSONL files as not approved.
- Existing held-out suites are separate: 40 MSA prompts and 30 Egyptian Arabic prompts. Do not move them into training.
- Existing source-approval, preflight, training, model-profile, evaluation, and human-release-gate code already implements much of the intended safety workflow.
- The recent audited corpus measured 193,403 total tokens and a 29,938,688-parameter estimate for the arabic_30m profile. Its preflight correctly blocks that profile.
- Do not create duplicate data packs or weaken the existing approval/preflight gates.

## Current proposal in this PR
- arabic_dialogue_seed_proposed.jsonl: 20 newly drafted examples, still quarantined.
- The new read-only audit tool reports exact SHA-256, structural validity, duplicate IDs/prompts, role sequencing, and author-supplied dialect/category labels.
- Structural audit is not rights approval, factual review, dialect validation, or permission to train.

## Stage A — data curation
1. Review each proposed dialogue for factuality, naturalness, dialect, privacy, and duplication.
2. Confirm authorship and permitted use for this exact file; do not infer permission from the fact it was drafted for the project.
3. Run: python ai_engine/audit_quarantined_dialogue.py ai_engine/proposals/arabic_dialogue_seed_proposed.jsonl
4. Preserve its exact SHA-256 and character count. Only after explicit owner approval may a private approval record be added and a reviewed PR copy it into the active corpus.
5. Expand using original or clearly licensed sources with source-level provenance. Keep MSA and Egyptian balance visible in reports.
6. Split train/validation by source or conversation group. Keep the 40 MSA and 30 Egyptian held-out prompts strictly outside training.

Suggested next experiment milestone: 250k–500k clean, rights-cleared tokenizer tokens. This is a small controlled experiment target, not a promise of assistant capability. Grow toward 1–5M diverse tokens only after quality and compute are measured. Do not pad the corpus with duplicates.

## Stage B — architecture and tokenizer
1. Reproduce the baseline model configuration and tokenizer from the exact checkpoint metadata.
2. Verify parameter count from the instantiated model, not a rough profile estimate.
3. Compare the existing cpu_small profile against one modestly larger profile using the same split and evaluation set.
4. Record context length, vocabulary, actual parameter count, peak RAM/VRAM, tokens/sec, training time, validation loss, and checkpoint SHA-256.
5. Do not increase vocabulary/model size unless corpus scale and compute justify it. A tokenizer change requires matching embedding changes and a fresh checkpoint lineage.

## Stage C — training
- Train only a new candidate checkpoint after the source approval gate and preflight both pass.
- Preserve the original checkpoint unchanged.
- Save optimizer/scheduler state, tokenizer, config, data manifest, seed, commit SHA, and logs.
- Use deterministic source-group train/validation splits and early stopping.
- Never train on evaluation prompts or human-review worksheets.
- Keep private weights and source material out of public artifacts.

## Stage D — evaluation
- Run the fixed held-out MSA and Egyptian suites plus unseen challenge prompts.
- Treat loss/perplexity as diagnostics only.
- Have humans score correctness, relevance, Arabic naturalness, coherence, context retention, instruction following, uncertainty, and safety.
- Reject malformed, irrelevant, fabricated, repetitive, or unsafe answers. Keep the current best checkpoint unless the candidate demonstrably improves.

## Stage E — Safari and deployment
- Prove PyTorch/browser parity using the real private checkpoint, not synthetic fixtures alone.
- Measure iPhone memory, load size/time, generation latency, and thermal behavior.
- If on-device execution is not reliable, use a private owner-controlled inference backend; never silently route to a third-party model.
- Deploy only after explicit review of the exact checkpoint fingerprint. Keep JON2_CHAT_RELEASE_APPROVED=false until then.

## Stop conditions
Stop if rights are unclear, data leakage is detected, loss becomes non-finite, checkpoint/tokenizer hashes mismatch, outputs regress, resource use exceeds budget, or privacy/safety gates fail.
