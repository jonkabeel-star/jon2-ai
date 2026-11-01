# Jon2 AI — Original Arabic Dataset Build Plan

## Purpose

Build a legally usable, high-quality Arabic conversation corpus for training Jon2 from random initialization. This plan is a data-collection specification, not a claim that the current corpus is sufficient.

## Non-negotiable rules

- Do not copy private chats, customer records, messages, or personal documents into the corpus without explicit permission from the people concerned.
- Do not scrape websites or books unless their license clearly permits the intended collection, modification, and model-training use.
- Record the source and license/permission for every contributed batch.
- Do not create synthetic duplicates just to increase character counts.
- Keep raw datasets and personal information outside the public Git repository.
- Keep the held-out test set private and never train on it.
- Remove names, phone numbers, email addresses, addresses, account details, and other identifying information before training.
- A passing automated audit does not establish copyright clearance, privacy clearance, factual accuracy, or model quality.

## Conversation record format

The audit tool accepts either:
- `{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`
- `{"prompt":"...","response":"..."}`
- `{"instruction":"...","input":"...","output":"..."}`
- `{"question":"...","answer":"..."}`

Use UTF-8 JSONL: exactly one JSON object per line. Keep each conversation self-contained and natural. Prefer several useful turns over a single generic answer.

## Suggested coverage matrix

Collect original, reviewed examples across these areas. The suggested proportions are planning targets, not a requirement to pad weak categories.

| Area | Suggested share | What good examples should teach |
|---|---:|---|
| Everyday Arabic conversation | 20% | Natural Egyptian Arabic and clear Modern Standard Arabic, appropriate tone |
| General knowledge and explanation | 20% | Explain concepts accurately, distinguish facts from uncertainty |
| Reasoning and step-by-step help | 15% | Break down tasks, show valid steps, check conclusions |
| Writing and summarization | 15% | Draft, rewrite, summarize, preserve user intent |
| Practical tasks and planning | 10% | Ordered steps, realistic constraints, useful follow-through |
| Creative writing | 10% | Coherent plots, consistent characters, satisfying endings |
| Safety and uncertainty | 10% | Refuse harmful requests appropriately, avoid fabricated facts, ask when essential |

## Quality review checklist

For each proposed conversation, a human reviewer should verify:
1. The user request and assistant response are relevant to each other.
2. The response is factually sound or clearly marks uncertainty.
3. Arabic is readable and does not contain accidental language mixing.
4. No repeated filler, copied templates, or contradictory turns.
5. No private or identifying information remains.
6. The source and reuse permission are documented.
7. The example teaches a reusable behavior rather than a one-off answer tied to hidden context.

## Dataset split and leakage prevention

- Assign a stable conversation ID before splitting.
- Split by conversation, not by individual message or line.
- Keep near-duplicates and paraphrases in the same split.
- Use a fixed, documented random seed when a random split is used.
- Never move test examples into training after inspecting model results.
- Keep the final test set untouched until evaluation.

## Readiness gates

Before any substantial training run:
- Resolve all parse errors, empty answers, duplicate examples, and train/test overlap.
- Manually review all possible privacy flags.
- Verify documented rights/permissions for every source.
- Expand beyond the current small corpus with genuinely new reviewed examples.
- Meet the existing minimum training-size guardrail; do not lower it merely to make training start.
- Run a small controlled pilot only after these gates pass, then evaluate on the untouched test set.

## Current project status

The repository contains tooling for aggregate-only corpus auditing. The actual private corpus is not stored here. The audit utility reports counts and possible contact-detail flags without printing source conversation text. A successful audit is only a structural check.
