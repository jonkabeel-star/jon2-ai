# Preliminary Human-Readable Review — Egyptian Arabic Draft 01

Review date: 2026-11-09
Source file: `ai_engine/data_drafts/egyptian_dialogue_draft_01.txt`
Source commit: `00da8afc90da770259e2750af969f7ac6d3a6043`
Source blob SHA: `38787bb4197371be47125f479d737bc944b398b6`
Measured UTF-8 text length reported by GitHub readback: 14,328 characters
Structural count: 80 user turns + 80 assistant turns; all non-comment dialogue lines are balanced.

## Decision

**HOLD — not approved for training, commercial use, redistribution, deployment, or public release.**

This is a content-quality screening based on reading the complete draft. It is not independent proof of authorship, provenance, rights ownership, consent, or legal permission. The file's own statement that the examples are original is a claim in the file, not independently verified evidence. No training approval is granted.

## Positive observations

- The draft uses recognizable Egyptian colloquial forms such as "إزيك", "عايز", "ممكن", and "متقلقش" without relying on insulting or abusive language.
- Most answers are concise, respectful, and appropriately ask for clarification when context is missing.
- Arithmetic examples checked in the draft are correct: 200 - 75 - 40 = 85; 200 - 75 - 50 = 75; and 100 - 80 - 7 = 13.
- Several answers appropriately express uncertainty rather than inventing live sports results or current facts.
- The privacy, credentials, medical, and destructive-file-operation examples are generally cautious and safety-oriented.

## Issues to fix before considering approval

1. **Dialect consistency:** Some answers mix Egyptian colloquial speech with formal written constructions. This is acceptable for a mixed register only if the dataset labels the intended register; otherwise normalize or tag each example.
2. **Awkward phrasing:** Review phrases such as "حسب هدفك ومدة الاستثمار وقدرتك على تحمل الخسارة والبلد والقوانين المتاحة" (investment answer), "التكلفة هي اللي بتدفعه عشان تشتري أو تنتج الحاجة" (grammar/agreement), and "المهمة اللي تأخيرها هيعمل أكبر مشكلة" (wording). Rewrite for naturalness and precision.
3. **Factual precision:** The definition of price/cost and the examples involving AI-powered maps should be tightened so they do not overgeneralize. Financial examples should clearly distinguish purchase cost, selling price, other expenses, gross margin, and net profit.
4. **Context structure:** The 80 pairs appear as one continuous sequence without explicit conversation/session IDs. Some examples rely on previous turns ("الجملة فوق", "خليها زي اللي فاتت", "طب ليه؟"). Add conversation IDs and turn indices, or mark context-dependent examples as multi-turn groups; do not shuffle individual turns independently.
5. **Evaluation leakage risk:** The separate 30-prompt evaluation file covers several of the same scenarios and includes a near-identical live-match question. Compare exact and near-duplicates across draft and evaluation data before any split. Keep evaluation prompts out of training.
6. **Originality and provenance:** The header says the examples are original and not copied from private conversations, but this cannot be proven from the text alone. Preserve authoring records and verify that no third-party or private conversational material was used.
7. **Coverage balance:** The draft is dominated by general assistant behavior, definitions, and short advice. It has limited examples of multi-step reasoning, Egyptian morphology/spelling variation, realistic longer context, code-switching, and domain-specific Egyptian vocabulary. Add original examples only after review; do not pad with repetitive variants.
8. **Annotation quality:** Add per-example labels for topic, dialect/register, single-turn vs multi-turn, safety category, factual verification requirement, and reviewer status. Do not place personal data or raw reviewer notes in the public repository.

## Required follow-up gates

- Verify author/provenance evidence and intended-use permission outside the public repository.
- Run exact and near-duplicate checks against the held-out evaluation set and all approved corpora.
- Have a fluent Egyptian Arabic reviewer review every example, including dialect naturalness and spelling.
- Fact-check factual claims and arithmetic; mark claims requiring live sources as tool-dependent.
- Create a private approval record tied to the exact source SHA-256 and an explicitly stated intended use.
- Re-run rights, privacy, quality, and split-integrity gates after every edit. Any edit changes the fingerprint and invalidates prior approval.

## Explicit non-actions

No training was run. No data was moved into the training directory. No model weights or checkpoints were created, replaced, or deleted. No chat release or publication setting was changed.
