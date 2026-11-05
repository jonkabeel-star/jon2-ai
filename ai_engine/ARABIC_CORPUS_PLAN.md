# Arabic Corpus Quality and Coverage Plan

## Purpose

This document defines a practical curation target for the first useful Arabic training experiments. It is a sampling plan, not a claim that a particular corpus size guarantees assistant quality. All sources must pass the source-rights approval gate before they are added to training.

## Current measured baseline (verified 2026-11-05)

The latest CI inventory found 5 UTF-8 text files with 290,513 raw Unicode characters, 515,830 bytes, and 184,342 tokens using a temporary 512-entry byte-BPE tokenizer. These token counts are corpus/configuration-specific and are not a model-quality score.

The structural audit counted 284,621 characters after removing blank and metadata-comment lines and reported 27 exact normalized duplicate groups. The privacy-aware audit reported 40 excess repeated lines; these require pair-level human review because short repeated follow-up prompts may have different paired answers. Its two phone-like matches were ISO date stamps in metadata headers, not contact details; a date-aware regression fix is being verified in CI.

The training approval gate remains BLOCKED because the private exact-file approval manifest is absent. The current token inventory is below the 250,000–500,000-token first-experiment target. No training has been run and no checkpoint exists.

## Historical seed-corpus baseline (2026-11-04)

The automated audit on 2026-11-04 reported:
- 15,674 characters in the combined `.txt` files counted by the language audit (including the join newline).
- 11,884 Arabic letters.
- All 36 tracked Arabic letter forms/characters appeared; none were missing.
- 2,418 Arabic word tokens.
- 1,332 unique normalized words.
- Lexical diversity: 0.5509 (unique normalized words divided by word tokens).

The separate structural audit reports 15,025 characters across the two original seed files. The totals differ because the language report includes a joining newline and counts the complete current text files using its own character definition. Use each audit for its stated metric; do not treat these small-seed numbers as a production benchmark.

The 36-character inventory includes hamza/alif variants and other tracked forms; it is not a claim that the basic Arabic alphabet has 36 independent letters.

## Character-frequency policy

- Do not force every Arabic letter to the same percentage.
- Do not set a fixed target percentage for alif, lam, meem, or any other letter.
- Natural Arabic letter frequencies are highly unequal. The measured seed corpus has alif (ا) at 14.77%, lam (ل) at 10.49%, and meem (م) at 8.09%; the tracked rare letter ظ is 0.21%. These are observations about this tiny project corpus, not universal Arabic-language frequencies.
- Improve rare-letter coverage through real words and diverse sentences: ظ مثل «ظاهرة، ظرف، عظيم»، ض مثل «ضوء، ضمير، ضرورة»، ث مثل «ثقافة، ثابت، تأثير»، ذ مثل «ذكي، تجربة، غذاء»، غ مثل «غدًا، تغيير، مغامرة». Examples are illustrative; curate complete natural sentences rather than appending word lists.
- Preserve spelling, hamza, ta marbuta, alif maqsura, diacritics, punctuation, and dialect distinctions in source text. Normalization may be used for analysis only, not to overwrite the corpus.

## Suggested content mix for a first curated corpus

Use these as approximate sampling shares across useful examples, not hard quotas. Review overlap and avoid duplicating the same text across categories.

| Content family | Initial share | What to include |
|---|---:|---|
| Everyday questions and helpful answers | 20% | Natural conversations, explanations, follow-up questions |
| General knowledge and educational explanations | 15% | Science, technology, geography, everyday concepts with checked facts |
| Instructions and procedural tasks | 15% | Ordered steps, constraints, clarification, troubleshooting |
| Reasoning and relationships | 10% | Cause/effect, comparison, conditions, arithmetic, inference |
| Summarization and rewriting | 10% | Short and long passages with faithful summaries |
| Stories and connected writing | 10% | Consistent characters, event order, coherent endings |
| Language and meaning | 10% | Polysemy, morphology, roots, synonyms, idioms, metaphor, grammar |
| Egyptian Arabic and register variation | 5% | Colloquial input with accurate MSA responses; preserve dialect as dialect |
| Safety, uncertainty, and privacy | 5% | Scam recognition, refusing unsupported claims, asking for clarification |

## Staged size targets

These are engineering milestones for experiments, not guarantees:
1. **Pipeline gate:** the existing 100,000-character minimum only prevents trivially tiny runs; it does not indicate useful assistant capability.
2. **First controlled experiment:** aim for roughly 250,000–500,000 clean Arabic tokens, after rights review, with held-out evaluation kept separate. Use this only to measure whether the training pipeline learns stable language patterns.
3. **Broader prototype:** work toward 1–5 million diverse, deduplicated Arabic tokens, then evaluate by domain and answer quality. This remains a small-model research stage, not a promise of ChatGPT-level performance.
4. Increase beyond this only after measuring model capacity, compute, validation loss, held-out answer quality, and dataset quality.

Count tokenizer tokens with the actual project tokenizer before training. Do not convert characters to tokens using a guessed fixed ratio.

## Quality checks for every source

- Exact source URL, licence/version, collection date, attribution requirements, and evidence of rights to the underlying text.
- No private conversations, secrets, personal data, or material without a documented legal basis.
- Language and script checks; remove malformed encoding and boilerplate.
- Exact and near-duplicate detection; do not inflate size by repeating examples.
- Domain labels and provenance retained in a private manifest.
- A held-out split created before training; keep all related passages and paraphrases in the same split to reduce leakage.
- Human review of factual accuracy, Arabic fluency, relevance, and safety.

## Meaning and context are learned from examples

To teach contextual meaning, include contrastive examples where the same word appears in different sentences, pronouns with clear and ambiguous antecedents, negation and conditionals, cause/effect, temporal order, idioms versus literal meanings, and multi-turn dialogue. A vocabulary list alone cannot teach these relationships.

The 40-prompt held-out set in `evaluation/prompts_ar.jsonl` tests many of these skills. It must remain outside the training corpus. A successful test-file load is not a model-quality result; score actual checkpoint answers with `EVALUATION_RUBRIC.md`.

## Current decision

Do not start training from the current corpus. Although it exceeds the trainer's 100,000-character guard, the inventory is only 184,342 temporary BPE tokens, below the 250,000–500,000-token first-experiment target; duplicate prompts still need pair-level review; and the private exact-file source-approval manifest is absent. First complete owner review and rights approval for each exact file, curate and evaluate the material, and confirm a real GPU/compute device before any training run.
