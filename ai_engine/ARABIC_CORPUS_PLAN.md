# Arabic Corpus Quality and Coverage Plan

## Purpose

This document defines a practical curation target for the first useful Arabic training experiments. It is a sampling plan, not a claim that a particular corpus size guarantees assistant quality. All sources must pass the source-rights approval gate before they are added to training.

## Current measured baseline (verified from CI on 2026-11-05)

The latest Python inventory on commit `e2c89144e7635a388ad1f81aa818c567fd31c454` found 5 UTF-8 text files, 290,513 raw Unicode characters, and 184,342 tokens using a temporary 512-entry byte-BPE tokenizer. These are corpus/configuration-specific inventory metrics, not a model-quality score.

The corpus-quality audit reported 28 exact normalized duplicate-line groups and 40 excess repeated lines. It found no Unicode replacement characters, unexpected control characters, or zero-width/BOM characters in the scanned files. These automated checks are limited: exact duplicate detection does not detect paraphrases, and privacy pattern scans are not complete privacy reviews.

The current approval gate remains BLOCKED because the private exact-file approval manifest is absent (`training_permitted=false`). The inventory is below the 250,000–500,000-token first-experiment target. No training was run and no release-ready checkpoint was created.

Paragraph-level train/validation splitting reduces direct paragraph overlap, but identical lines can still occur in different paragraphs and may cross the split. Keep related material together during human curation; do not mechanically delete repeated lines because short follow-up prompts can have different paired answers.

All reported values above are from the successful Python workflow run `41999747352` on commit `e2c89144e7635a388ad1f81aa818c567fd31c454`.

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


## Superseding project status — 2026-11-05 (verified after the first real training run)

This section supersedes the earlier "Current decision" statement above for the historical first experiment. The earlier statement accurately described the state at workflow run `41999747352`, but it is no longer the latest project state.

- Owner approval was given for the exact five project-authored files only: `original_dialogue_ar.txt`, `original_dialogue_ar_batch_01.txt`, `original_dialogue_ar_batch_02.txt`, `original_dialogue_ar_batch_03.txt`, and `original_seed_ar.txt`. The training workflow used the private exact-file approval manifest and hash checks. This approval does not extend to any new file, external dataset, or future revision with changed bytes.
- A real PyTorch CPU training run completed in GitHub Actions: [run 42027297208](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42027297208). It ran 1,200 optimizer steps; the best validation checkpoint was at step 900 with validation loss 3.6355. The resumable last checkpoint was at step 1,200. The model had 269,952 parameters.
- Training corpus metrics from that run: 289,120 Unicode characters; 185,697 training tokens and 20,679 validation tokens. These are actual training-run measurements and are distinct from the earlier temporary byte-BPE inventory.
- The private checkpoint was evaluated on 40 held-out Arabic prompts in [run 42028581017](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42028581017). The generated answers were fragmented and not sufficiently understandable or coherent. The run completing successfully means the evaluation process ran; it does not mean the model passed.
- **Current release decision: BLOCKED.** Do not set `JON2_CHAT_RELEASE_APPROVED=true`, do not present this checkpoint as a working assistant, and do not deploy it for public chat.
- The next work is model/data quality diagnosis and a better controlled experiment plan. Do not start another training run merely by repeating the same corpus and settings. Any new training source or changed source file requires a separate explicit owner approval and rights review first.
- Public-repository structural audit snapshot (workflow run `42067766282`): the five tracked text files totaled 284,621 characters and contained 27 exact normalized duplicate lines. This public snapshot is not the same measurement as the training-run corpus; do not merge or substitute these metrics. The audit's structural pass does not establish factual accuracy, fluency, or legal rights.

The first real training experiment is therefore complete as an engineering milestone but failed the human-facing answer-quality gate. The project is in model-quality improvement, not chat release.
