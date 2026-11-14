# Jon2 Phase 5 — 100-question held-out Arabic evaluation

Status: dataset prepared; inference was NOT run by this PR.

- 100 prompts: 50 MSA and 50 Egyptian Arabic.
- Dataset: `phase5_prompts_100.jsonl`.
- Every record is `evaluation_only` and `training_eligible=false`; never use these prompts for training/SFT.

## Run protocol
1. Execute only against the owner's private original Jon2 checkpoint in its authorized private runtime (such as the owner's Kaggle session). Never upload weights to GitHub or substitute another model.
2. Record checkpoint SHA-256, tokenizer SHA-256, code commit, runtime/device, generation settings and timestamp.
3. Generate one answer per ID and preserve exact prompt IDs/text. Missing or failed generations must be marked failed, never filled with placeholders.
4. Export the exact 100 prompt/answer pairs and fingerprints in a JSON report.
5. Human reviewers score each answer 0–4 for Arabic fluency, coherence/meaning, instruction following, factuality/reasoning and safety; review MSA and Egyptian separately and document defects.

Automatic character/length/repetition metrics are diagnostics only. This phase does not train the model, alter weights, approve a checkpoint, enable chat or authorize deployment. Public chat remains blocked until the exact checkpoint passes `ai_engine/HUMAN_REVIEW_GATE.md`.
