# Jon2 Arabic Research Corpus Intake — Private Only

Date reviewed: 2026-11-25

## Scope

This intake is for a **private, non-commercial research checkpoint only**. It does not grant rights to publish raw datasets, release derived weights, or use any research-only data in a commercial Jon2 service.

The source registry is `research_candidate_registry.json`. It is a shortlist, not an approval manifest. Every source remains blocked until its exact upstream terms and provenance have been reviewed. No dataset files are committed to this repository.

## Candidate triage

| Candidate | Declared terms | Intended role | Current decision |
|---|---|---|---|
| TheArabicPile Conversational | CC BY-NC 4.0 | MSA/general Arabic candidate | Access, provenance, and exact revision review required |
| NileChat FineWeb-Edu Egypt | CC BY-NC 4.0 | Egyptian Arabic text candidate | Upstream FineWeb-Edu rights and machine-translation provenance review required |
| NileChat Arabizi-Egypt | CC BY-NC 4.0 | Optional Arabizi coverage | Upstream rights review required; keep separate from Arabic-script data |
| Alexandria | CC BY-NC-ND 4.0 | Potential held-out dialect benchmark | Evaluation/legal review only; no training without written rights-holder confirmation |
| ArSyra Chatbot | CC BY-NC-SA 4.0 | Dialogue-quality candidate | Gated access, non-redistribution, and ShareAlike implications review required |
| fr3on Egyptian Dialogue | Uploader declares CC BY 4.0 | None yet | Quarantine because TV subtitle provenance does not establish underlying rights |

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

## Non-negotiable gates

- Never add raw datasets, checkpoints, tokens, or private manifests to Git.
- Never infer training permission from a dataset name or a license badge alone.
- Never train on the held-out test partition or use it for checkpoint selection.
- Never mark semantic quality or public release as approved automatically.
- Never set `JON2_CHAT_RELEASE_APPROVED=true` as part of research training.
- Keep the original checkpoint intact; all new runs are candidate checkpoints until review.
