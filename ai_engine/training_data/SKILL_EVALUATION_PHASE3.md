# Jon2 phase 3: skill evaluation foundation

This phase adds a conservative validator and scorer for skill-evaluation records
covering mathematics, logic, science, programming, and instruction following.

## Important boundaries

- Every record must declare split as evaluation_only; the loader rejects any
  training split. Held-out prompts and these skill records must never be mixed
  into SFT or pretraining data.
- New records remain in quarantine until a human checks correctness,
  provenance, license, privacy, and suitability.
- Every record carries a source reference, license basis, and SHA-256 value.
  The validator checks hash shape, not whether the source is genuine or rights
  are actually cleared.
- Exact-text and numeric checks are deliberately narrow. Logic, science,
  instruction following, and programming require human review by default.
- Submitted code is never executed. This module is not a sandbox.
- A passing deterministic check is not proof of reasoning or general
  understanding.

## Record shape

Each JSONL record contains id, domain, prompt, reference_answer, verifier,
verification_notes, source (reference, license, sha256), review_status, and
split. Numeric tasks may also specify a non-negative tolerance. Use the human
verifier whenever a single exact reference cannot reliably establish correctness.

## Use

load_skill_tasks(path) validates JSONL records and duplicate IDs.
evaluate_response(task, response) returns correct, incorrect, or
needs_human_review. Human-review cases are not silently counted as correct or
incorrect. summarize_results preserves that separate category.

No skill corpus is created or approved by this change. No model training,
fine-tuning, checkpoint write, weight change, or deployment is performed.
