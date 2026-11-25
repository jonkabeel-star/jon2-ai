# Jon2 Arabic Research Corpus Intake — Private Only

Date reviewed: 2026-11-25

## Scope

This intake is for a **private, non-commercial research checkpoint only**. It does not grant rights to publish raw datasets, release derived weights, or use any research-only data in a commercial Jon2 service.

The source registry is `research_candidate_registry.json`. It is a shortlist, not an approval manifest. Every source remains blocked until its exact upstream terms and provenance have been reviewed. No dataset files or private approvals are committed to this repository. `source_approvals.example.json` is a placeholder template only; copy it to the private data volume, replace all placeholders, and mark an exact file `APPROVED` only after a human rights/provenance review.

## Candidate triage

| Candidate | Declared terms | Intended role | Current decision |
|---|---|---|---|
| TheArabicPile Conversational | CC BY-NC 4.0 | MSA/general Arabic candidate | Access, provenance, and exact revision review required |
| NileChat FineWeb-Edu Egypt | CC BY-NC 4.0 | Egyptian Arabic text candidate | Upstream FineWeb-Edu rights and machine-translation provenance review required |
| NileChat Arabizi-Egypt | CC BY-NC 4.0 | Optional Arabizi coverage | Upstream rights review required; keep separate from Arabic-script data |
| Alexandria | Conflicting CC BY-NC 4.0 current card vs CC BY-NC-ND 4.0 pinned revision | None until resolved | Quarantined; no intake/training pending written rights-holder clarification |
| ArSyra Chatbot | CC BY-NC-SA 4.0 | Dialogue-quality candidate | Gated access, non-redistribution, and ShareAlike implications review required |
| fr3on Egyptian Dialogue | Uploader declares CC BY 4.0 | None yet | Quarantine because TV subtitle provenance does not establish underlying rights |
| ShawarmaChats | CC BY-SA 4.0 | MSA/Egyptian/Maghrebi multi-turn dialogue | 28,500 train / 1,512 official test; Wikipedia-grounded, AI-generated and rated/repaired; ShareAlike review required |
| QCRI WASIL | CC BY-NC-SA 4.0 | Held-out spoken-assistant evaluation | 9,304 prompts with feedback; keep test/feedback splits isolated; data viewer currently reports invalid audio paths |
| 4FACTORS Egyptian sample | CC BY-NC 4.0; access-gated | Potential human-reviewed smoke test only | Request-access gate; no request or terms acceptance; 50 pairs only |
| fr3on Arabic Dialect Corpus | Uploader declares MIT | None yet | Quarantine: YouTube comments, upstream rights/platform terms/privacy review required |
| Bayanat Open Arabic Books | CC BY 4.0 dataset; per-book colophon rights | General Arabic long-form text | 1,545 books / 54.2M body words; per-title rights and Egypt-specific review required |
| Bayanat Arabic Wikipedia Monthly (Egyptian) | CC BY-SA 4.0 | Egyptian Arabic encyclopedic text, not dialogue | 1.63M articles; begin with 50,971 rule-flagged human-written articles; ShareAlike and quality review required |

## Training phases

1. **Rights and provenance:** pin immutable dataset revisions; capture license text, upstream source, access terms, attribution, and allowed research scope. Reject uncertain sources.
2. **Private intake:** download only approved sources to storage outside the Git checkout. Record SHA-256 and exact counts. Keep raw data private.
3. **Quality filtering:** remove duplicates, corrupted records, non-Arabic noise, personally identifying data, low-quality machine translations, and malformed conversations. Keep MSA, Egyptian Arabic script, and Arabizi in separately tagged strata.
4. **Leakage-safe split:** split by conversation/source groups into train, validation, and held-out test before fitting the tokenizer. Keep test files inaccessible to the trainer and checkpoint selector.
5. **Capacity preflight:** calculate actual post-filter token count and compare it with the selected model's parameter count. The existing `arabic_30m` profile is configuration only; it is not trained weights.
6. **Staged training:** train a small smoke-test candidate first, then the full `arabic_30m` candidate only if GPU memory, corpus scale, and preflight all pass. Save resumable checkpoints privately and retain hashes.
7. **Evaluation:** run single-word intent, sentence meaning, Egyptian/Fusha, reasoning, instruction-following, and multi-turn context suites. Automatic scores are diagnostic only.
8. **Human review:** two-pass review of held-out answers with documented scores and failure examples. A failed answer-quality gate blocks release.
9. **Release separation:** research-only sources and checkpoints remain private. A commercial/public model needs a separate source-rights audit and separate approval.

## Current infrastructure blocker

The existing GitHub Actions workflow `.github/workflows/jon2-private-gpu-training.yml` requires a self-hosted Linux x64 runner labelled `jon2-gpu`, CUDA, and private storage paths in repository variables `JON2_PRIVATE_DATA_DIR` and `JON2_PRIVATE_CHECKPOINT_DIR`. It also requires a private exact-file approval manifest. This workflow is manually dispatched and does not provision a GPU server.

No training run should be dispatched until that runner is online, the private paths are configured, the approved corpus passes preflight, and the training plan is confirmed. Do not substitute a hosted CPU runner or the user's iPhone for GPU training.

## Newly identified dialogue candidates

The current card for ShawarmaChats describes 30,012 six-turn conversations: 28,500 train and 1,512 test, across MSA, Egyptian and Maghrebi. It is grounded in Arabic Wikipedia; dialogues were generated by Gemini 2.5 Flash, graded/repaired, and a small remainder corrected by native speakers. The card declares CC BY-SA 4.0. A dedicated adapter is provided at `ai_engine/datasets/adapters/ingest_shawarmachats.py`. It:
- requires an immutable Hugging Face revision SHA;
- filters dialects (default MSA and Egyptian);
- converts only the official train split into a private JSONL file;
- writes the official test split into a separate `evaluation-only/` directory;
- records hashes, counts, dialects, page IDs, URLs, and attribution;
- requires explicit private-research and ShareAlike review flags;
- never creates `source_approvals.json` or starts training.

The 4FACTORS sample contains 50 native-written Egyptian question/answer pairs under CC BY-NC 4.0 and is suitable only for a small human-quality smoke test. WASIL is evaluation-only for now: 9,304 spoken Arabic assistant prompts with human feedback, under CC BY-NC-SA 4.0, and the current Hugging Face viewer reports invalid audio paths. The new fr3on Arabic dialect corpus declares MIT but consists of YouTube comments; the underlying user content rights and platform terms remain unresolved, so it stays quarantined.

## Dataset format gate

The current three-way dialogue trainer accepts structured UTF-8 JSONL records shaped as `{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`, with complete alternating user/assistant turns. It does not directly ingest arbitrary Parquet, scraped web pages, or plain-text corpora as dialogue. Each candidate source therefore needs a separately reviewed adapter/normalization step that preserves source IDs and attribution. No candidate dataset has yet been downloaded, transformed, or approved. A source must not be converted into synthetic assistant turns or labelled as a conversation when its original data does not contain that structure.

## Corrected training workflow integration

The manual GPU workflow now follows the existing three-way dialogue pipeline instead of the older source-file-only split:

1. Validate the private data/checkpoint directories and CUDA GPU.
2. Run `prepare_dialogue_splits.py` against the exact-file approval manifest to create train, validation, and held-out test partitions under private checkpoint storage.
3. Run `preflight_dialogue_training.py`, which loads only train/validation text, hash-checks the test partition without decoding it, and blocks below the configured corpus/token-per-parameter thresholds.
4. Train with both `--dialogue-splits-dir` and `--candidate-only`; candidate checkpoints must live in a private `candidates/` directory.
5. Hash the candidate and bind its manifest to the split-manifest SHA-256. Run the existing MSA/Egyptian diagnostic prompts.
6. Keep the held-out test partition reserved for a separate evaluation and human review. Automatic diagnostics are not a semantic pass.

The workflow remains manual and requires the exact confirmation phrase, an online `jon2-gpu` runner, CUDA, private storage variables, and a valid exact-file approval manifest. This integration has been committed to the draft PR branch only; it has not been run on a GPU and does not mean a checkpoint has been trained or approved.

## Non-negotiable gates

- Never add raw datasets, checkpoints, tokens, or private manifests to Git.
- Never infer training permission from a dataset name or a license badge alone.
- Never train on the held-out test partition or use it for checkpoint selection.
- Never mark semantic quality or public release as approved automatically.
- Never set `JON2_CHAT_RELEASE_APPROVED=true` as part of research training.
- Keep the original checkpoint intact; all new runs are candidate checkpoints until review.


## Staged Arabic evaluation added

The evaluation-only harness `ai_engine/evaluate_staged_arabic.py` runs in this order:
1. Single-word intent recognition (greetings, thanks, questions, help, agreement, negation, continuation).
2. Short MSA and Egyptian sentence understanding and instruction following.
3. Multi-turn context retention and follow-up consistency.

It writes the checkpoint SHA-256 and every generated answer into a review report. Human score fields start empty; all human pass flags and release approval start false. The harness is diagnostic and cannot approve a checkpoint. Run it only against a private candidate checkpoint, for example:

```bash
PYTHONPATH=ai_engine python ai_engine/evaluate_staged_arabic.py \
  --checkpoint /private/checkpoints/candidates/jon2-candidate.pt \
  --output /private/checkpoints/candidates/staged-evaluation.json
```

The original `jon2-last.pt` remains read-only. Training workflow writes only under the separate candidate directory and does not overwrite or replace the original checkpoint. No training is authorized by adding this evaluator.


## Rights recheck (2026-11-25)

See `DATA_SOURCE_RIGHTS_RECHECK_2026-11-25.md` for the exact page/revision findings. Alexandria is quarantined due conflicting license declarations across revisions. 4FACTORS is access-gated and no access request was made. ShawarmaChats remains a candidate pending ShareAlike/model-weight review and immutable revision pinning. Open Arabic Books and Egyptian Arabic Wikipedia Monthly were added as text-only candidates, both requiring per-source rights and quality review. No source is approved and no data was downloaded.
