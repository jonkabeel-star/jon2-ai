# Jon2 AI — Arabic dialogue candidate batch 500 v1

- Count: 500 one-turn Arabic user/assistant examples.
- Topics: 20 everyday learning, reasoning, digital-literacy, and practical-skill domains; 25 examples per topic.
- Origin: newly authored synthetic examples for this project; no external corpus was imported.
- Status: **candidate only**. Every JSONL record has `review_status: candidate_only` and `training_eligible: false`.
- Storage: `ai_engine/data_candidates/`, deliberately outside `ai_engine/training_data/`.
- This file is not an approval record, does not change any rights manifest, and must not be used for training until the owner has reviewed the content and explicitly approves a separately versioned batch.

## Automated structural and editorial checks

The batch has 500 records, 500 unique IDs, 500 unique user prompts, 500 unique assistant responses, 20 topics with 25 examples each, no empty messages, Arabic text in every user and assistant message, and consistent candidate-only flags. A dedicated unittest suite now checks JSONL parsing, topic balance, uniqueness, candidate-only safeguards, Arabic presence, repeated topic-prefaces, punctuation defects, and first-step phrasing.

These automated checks catch structural defects and a few known editorial regressions. They do **not** prove that an answer is factually correct, fully answers its prompt, sounds natural to native speakers, or is safe for every context.

## Language-quality revision

The latest editorial pass replaced repeated generic answers with topic-specific measurement criteria, review triggers, practical examples, and follow-up actions across all 20 topics. It also removed identical answer strings that had appeared across topics and corrected an awkward first-step construction.

This remains **machine-assisted candidate text**, not a human-reviewed gold dataset. Some answer structures are still reusable, and a zero-duplicate count is not evidence of natural language quality. Human review is still required for:
- whether each answer fully addresses its exact question;
- Arabic grammar, idiom, and natural phrasing;
- factual accuracy and safe advice, especially in digital security, finance, food safety, and news verification;
- Egyptian colloquial vs Modern Standard Arabic balance;
- semantic repetition and suitability for the intended model.

## Review and rights safeguards

Reject or edit any example that is repetitive, vague, inaccurate, unnatural, or too generic. Keep reviewed content separate from training inputs. Do not modify `approved_sources.json`, `source_approvals.json`, training manifests, checkpoints, or training workflows as part of this review. No example in this batch is approved for training.
