# Egyptian Arabic quality work — draft only

This directory contains original Egyptian Arabic dialogue examples for owner review.
The material is deliberately outside `ai_engine/training_data/` so existing training
commands cannot ingest it by default.

## Status and restrictions

- The dialogue file is a draft, not an approved training source.
- No training, checkpoint creation, checkpoint replacement, public-chat activation,
  or release approval is performed by adding these files.
- Review every response for dialect naturalness, factual correctness, privacy,
  originality, and consistency before considering training.
- After review, record the exact file SHA-256 and UTF-8 character count in the
  private source-approval manifest. Never add an approval record automatically.
- Keep the independent evaluation prompts in `ai_engine/evaluation/`; do not
  copy them into training data or use them to update model weights.
- Automated format tests verify structure only. They do not verify semantic
  correctness or human approval.

## Draft content

- `egyptian_dialogue_draft_01.txt`: original Egyptian Arabic multi-turn dialogues.
- `../evaluation/egyptian_arabic_prompts_draft.jsonl`: held-out prompts with
  human review criteria, not reference answers or an automatic quality score.

The current 269,952-parameter checkpoint has previously produced incoherent
Arabic. This draft is a data-curation step, not evidence that the model can
already understand Egyptian Arabic.
