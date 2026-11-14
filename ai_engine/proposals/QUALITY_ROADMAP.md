# Jon2 quality roadmap — staged execution

## Current known blockers
- The historical ~269,952-parameter checkpoint generated visibly incoherent Arabic in the 40-prompt held-out evaluation.
- A later `arabic_30m` profile preflight measured 193,403 tokens in the audited corpus against a 29,938,688-parameter estimate and correctly blocked training.
- CI, checkpoint loading, and surface-level Arabic checks are not semantic quality evidence.
- Human approval remains mandatory; public chat must stay fail-closed.

## Stage A — data curation
1. Keep new material in this quarantine directory.
2. Review every dialogue for factuality, naturalness, dialect, privacy, and duplicate/near-duplicate overlap.
3. Record provenance, intended use, author/owner, license or permission evidence, exact SHA-256, and reviewer decision.
4. Move only explicitly approved sources into the active training corpus via a reviewed PR.
5. Keep training, validation, and held-out evaluation sources separated by source/conversation group, not by random adjacent lines.

Suggested early experiment milestone: 250k–500k clean, rights-cleared tokenizer tokens. This is a small controlled experiment target, not a promise of assistant capability. Work toward 1–5M diverse tokens only after quality and compute are measured. Do not pad the corpus with duplicates.

## Stage B — architecture and tokenizer
1. Reproduce the baseline model configuration and tokenizer from the exact checkpoint metadata.
2. Verify parameter count from the instantiated model, not a rough profile estimate.
3. Test a small set of configurations (baseline and one modestly larger profile) using the same split and evaluation set.
4. Record context length, vocabulary, parameter count, peak RAM/VRAM, tokens/sec, training time, validation loss, and checkpoint SHA-256.
5. Do not increase vocabulary/model size unless corpus scale and compute justify it. A tokenizer change requires a matching embedding resize and a fresh checkpoint lineage; do not silently reinterpret old weights.

## Stage C — training
- Train only a new candidate checkpoint on an isolated branch/run and a source manifest with exact hashes.
- Preserve the original checkpoint unchanged and private.
- Save optimizer/scheduler state, tokenizer, config, data manifest, seed, commit SHA, and logs.
- Use deterministic train/validation split by source group and early stopping based on validation behavior.
- Do not train on evaluation prompts or human-review worksheets.
- Never publish private weights or training data in the public repository/artifacts.

## Stage D — evaluation
- Run the fixed held-out MSA and Egyptian suites plus unseen challenge prompts.
- Measure loss/perplexity only as diagnostics; they do not prove understanding.
- Have humans score correctness, relevance, Arabic naturalness, coherence, context retention, instruction following, uncertainty, and safety.
- Reject malformed, irrelevant, fabricated, repetitive, or unsafe answers. Keep the current best checkpoint unless the candidate demonstrably improves.

## Stage E — Safari and deployment
- First prove checkpoint/tokenizer parity between PyTorch and the browser runtime using the real private checkpoint, not synthetic fixtures alone.
- Measure iPhone memory, first-load size, load time, generation latency, and battery/thermal behavior.
- If the model cannot run reliably on-device, use a private owner-controlled inference backend; do not silently route to a third-party model.
- Deploy only after explicit human review of the exact checkpoint fingerprint. Keep `JON2_CHAT_RELEASE_APPROVED=false` until then.

## Stop conditions
Stop a run if source rights are unclear, data leakage is detected, loss becomes non-finite, checkpoint/tokenizer hashes mismatch, outputs regress, resource use exceeds the declared budget, or any safety/privacy gate fails.
