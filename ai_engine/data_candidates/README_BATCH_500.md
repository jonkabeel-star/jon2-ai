# Jon2 AI — Arabic dialogue candidate batch 500 v1

- Count: 500 one-turn Arabic user/assistant examples.
- Topics: 20 everyday learning, reasoning, digital-literacy, and practical-skill domains.
- Origin: newly authored synthetic examples for this project; no external corpus was imported.
- Status: **candidate only**. Every JSONL record has `review_status: candidate_only` and `training_eligible: false`.
- Storage: `ai_engine/data_candidates/`, deliberately outside `ai_engine/training_data/`.
- This file is not an approval record, does not change any rights manifest, and must not be used for training until the owner has reviewed the content and explicitly approves a separately versioned batch.
- Automated checks performed at creation: 500 records, unique user prompts, non-empty Arabic user and assistant text, consistent candidate-only flags, and valid JSON serialization.
- Human review still required for factual accuracy, naturalness, repetition, dialect balance, and suitability for the intended model.

## Review guidance

Reject or edit any example that is repetitive, vague, inaccurate, unnatural, or too generic. Keep the reviewed artifact separate from training inputs. Do not modify `approved_sources.json`, `source_approvals.json`, training manifests, checkpoints, or training workflows as part of this review.
