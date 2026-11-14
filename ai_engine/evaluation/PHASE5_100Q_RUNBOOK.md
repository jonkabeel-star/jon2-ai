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

## Executable runner (private Kaggle runtime)

The repository now includes `ai_engine/run_phase5_evaluation.py`. It validates the exact 100-record 50/50 benchmark, refuses records not marked evaluation-only, computes SHA-256 fingerprints for the checkpoint and tokenizer, and records each generation as generated, empty, or failed. A failed generation is never replaced with invented text.

If KaggleHub returns HTTP 403, do not retry by embedding tokens in notebook code. In the Kaggle notebook UI, use **Add Input** to attach the owner's private checkpoint dataset (only if the account has access). Then locate the mounted checkpoint path with:

```python
from pathlib import Path
for path in Path("/kaggle/input").rglob("*.pt"):
    print(path)
```

Run from the repository root after the repository files are available in the notebook:

```bash
python ai_engine/run_phase5_evaluation.py \
  --checkpoint "/kaggle/input/PRIVATE_DATASET/checkpoint.pt" \
  --prompts ai_engine/evaluation/phase5_prompts_100.jsonl \
  --output /kaggle/working/phase5-review-report.json \
  --code-commit 711a51486cf393c03e04b072214a74002f294301
```

Replace only the checkpoint path with the exact path printed by the discovery cell. Keep the report in `/kaggle/working`; export the JSON report only. Do not export or upload checkpoint weights. If no `.pt` file appears under `/kaggle/input`, the private checkpoint is not attached/accessible and inference cannot proceed.
