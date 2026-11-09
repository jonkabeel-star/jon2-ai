# Jon2 AI — Arabic dialogue candidate batch 500 v1

- Count: 500 one-turn Arabic user/assistant examples.
- Topics: 20 everyday learning, reasoning, digital-literacy, and practical-skill domains; 25 examples per topic.
- Origin: newly authored synthetic examples for this project; no external corpus was imported.
- Status: **candidate only**. Every JSONL record has `review_status: candidate_only` and `training_eligible: false`.
- Storage: `ai_engine/data_candidates/`, deliberately outside `ai_engine/training_data/`.
- This file is not an approval record, does not change any rights manifest, and must not be used for training until the owner has reviewed the content and explicitly approves a separately versioned batch.

## Automated structural checks

The batch has 500 records, 500 unique IDs, 500 unique user prompts, 20 topics with 25 examples each, no empty messages, Arabic text in each user and assistant message, consistent candidate-only flags, and valid JSONL serialization. These checks establish structure only; they do not establish linguistic quality or factual correctness.

## Language-quality revision

A rule-guided editorial pass was applied to improve directness and remove repeated topic-prefaces and several mismatched generic answers. It also changed the generic "why" questions to the more natural "ما أهمية ...؟" form and rewrote the answer patterns for the 25 prompt intents using topic-specific definitions, practical steps, and cautions where available.

This is still **machine-assisted candidate text**, not a human-reviewed gold dataset. Some answer structures remain intentionally reusable across topics, so lexical uniqueness must not be confused with naturalness. Human review is still required for:
- whether each answer fully addresses its exact question;
- Arabic grammar, idiom, and natural phrasing;
- factual accuracy and safe advice;
- Egyptian colloquial vs Modern Standard Arabic balance;
- semantic repetition and suitability for the intended model.

## Review and rights safeguards

Reject or edit any example that is repetitive, vague, inaccurate, unnatural, or too generic. Keep reviewed content separate from training inputs. Do not modify `approved_sources.json`, `source_approvals.json`, training manifests, checkpoints, or training workflows as part of this review. No example in this batch is approved for training.
