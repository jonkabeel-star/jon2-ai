# Jon2 AI — Dataset Register

This register must be completed for every source before it is used in training or in a commercial/public model.

## Candidate 1: ArabicText-Large

- Dataset ID: `Jr23xd23/ArabicText-Large`
- Dataset page: https://huggingface.co/datasets/Jr23xd23/ArabicText-Large
- Dataset card declares Apache License 2.0 for the dataset release.
- Dataset card reports 743,288 articles and 244,153,780 words.
- The dataset's published sample/metadata identifies Wikipedia as a source for at least some records and includes Arabic Wikipedia source URLs.
- Intended role: possible Arabic pre-training text candidate, subject to source-rights review.
- Review performed: 2026-10-30 (public dataset card, license file, and sample metadata checked).
- Review finding: the Apache-2.0 declaration is not, by itself, enough evidence that the dataset publisher can relicense every underlying Wikipedia text under Apache-2.0. Wikipedia text is generally available under CC BY-SA terms (and in some cases GFDL); those terms can carry attribution and share-alike conditions. The dataset's record-level provenance and permissions need to be established.
- Status: **NOT APPROVED — DO NOT DOWNLOAD OR TRAIN ON THIS SOURCE FOR JON2 AI AT THIS TIME**.
- Reason: no independent evidence was found in the reviewed materials establishing that all underlying article text was separately cleared for unrestricted public/commercial model training or explaining how the applicable source-license obligations are satisfied.
- Next requirement: obtain written clarification from the dataset maintainers identifying the rights basis for the Wikipedia-derived text, the exact licenses applying to each source subset, and the intended model-training / public or commercial deployment permissions. If that cannot be established, exclude this dataset and use text written by Jon2 AI contributors or sources with clear, documented permissions for the intended use.

## Approval record

Do not change a candidate to APPROVED until all fields below are filled and reviewed:

- Reviewer:
- Review date:
- Exact license text/version for the dataset:
- Underlying content sources and per-source licenses:
- Written permission / rights basis for third-party content:
- Commercial model-training permission confirmed: YES / NO
- Attribution / notice requirements:
- Share-alike or model-distribution obligations:
- Decision and rationale:

**Current decision:** NOT APPROVED. Keep `RIGHTS_REVIEWED = False` in the Colab notebook. Do not run the downloader for this candidate.


## Candidate 2: Jon2 AI Original Arabic Seed

- File: `ai_engine/training_data/original_seed_ar.txt`
- Source: a small original starter text drafted specifically for the Jon2 AI project; it is not intentionally copied from external books, articles, websites, or datasets.
- Intended use: verify the local data-reading pipeline only.
- Rights status: project-originated draft; owner review and acceptance still required before training or public/commercial deployment.
- Size: small starter sample, not a useful general-purpose training corpus.
- Status: **REVIEW REQUIRED / PIPELINE TEST ONLY**.
- Handling: do not add third-party text to this file. Keep future training corpora private and out of the public GitHub repository.

## Current source decision

- ArabicText-Large: **NOT APPROVED**.
- HPLT web-crawl text: **NOT APPROVED** for this project on the basis of the published terms alone. HPLT states it does not own the extracted text and licenses only the packaging under CC0; it places responsibility for legal compliance on the user.
- Jon2 original seed: **PIPELINE TEST ONLY** until owner review and a much larger original corpus is prepared.

## Candidate 3: Jon2 AI Original Arabic Dialogue Draft

- File: `ai_engine/training_data/original_dialogue_ar.txt`
- Source: original Arabic question-and-answer examples drafted specifically for the Jon2 AI project in this development session; no external corpus or private user conversations were used.
- Intended use: initial pipeline and dialogue-format experiments.
- Rights status: original project-specific draft, subject to the repository owner's review and acceptance; this entry is not legal advice or a guarantee of commercial-use rights.
- Size: small starter set; not sufficient for a capable general-purpose assistant.
- Status: **DRAFT / OWNER REVIEW REQUIRED / NOT A PRODUCTION DATASET**.
- Handling: review accuracy and wording, expand with additional original or explicitly licensed material, and document each new source before training or public/commercial deployment.


## Candidate 4 — Arabic Wikipedia starter corpus (generated in Colab)

- Source: Arabic Wikipedia through the official MediaWiki API (https://ar.wikipedia.org/).
- Historical collection: a diverse collection run in Colab reportedly reached approximately 250,000 characters across 51 articles on 2026-10-30. This is historical session output, not currently available for independent verification.
- Current availability: the collected text and source manifest are absent from the freshly cloned repository and current Colab runtime.
- License: Wikipedia text is generally available under CC BY-SA 4.0; verify each article page and any source-specific notices.
- Attribution: the source manifest should record article titles, URLs, and categories; article histories identify contributors.
- Transformations: plain-text extraction, whitespace cleanup, removal of short/noisy lines, duplicate filtering, and possible truncation of the final article in the existing collector.
- Storage: keep the corpus and manifest in private Colab/Drive storage; do not commit training text or source manifests to the public GitHub repository.
- Status: COLLECTED HISTORICALLY / NOT PRESENT IN CURRENT RUNTIME / NOT APPROVED FOR TRAINING OR COMMERCIAL DEPLOYMENT. Recollect only as a quarantined research corpus and preserve its manifest.
- Important: CC BY-SA requires attribution and share-alike for adapted material. Do not assume model-weight licensing or commercial redistribution is automatically cleared; obtain a rights review for the intended use before training or release.

## Candidate 5 — Jon2 AI Original Arabic Dialogue Expansion Batch 01

- File: `ai_engine/training_data/original_dialogue_ar_batch_01.txt`
- Source: 815 user/assistant dialogue pairs drafted for the Jon2 AI project on 2026-11-04. The file header states that private conversations, copied web text, and third-party datasets were not used; this is a project-source declaration, not independent legal verification.
- Raw file size: 136,075 Unicode characters; SHA-256: `77f08523cfb85d2a69d1446451f9c797e95d6dd1d8cd7e509ef9c51826f0014f`.
- Intended role: candidate dialogue material for Arabic instruction following, multi-turn context, explanations, writing, programming concepts, evaluation literacy, privacy, and safe assistant behavior.
- Rights status: project-authored draft; owner review and explicit acceptance of this exact file and training use remain required. This entry is not legal advice or a guarantee that every legal right is cleared.
- Quality status: requires human review for factual accuracy, Arabic fluency, duplication, balance, and suitability. Automated structural checks cannot establish these qualities.
- Status: **DRAFT / OWNER REVIEW REQUIRED / NOT APPROVED FOR TRAINING**.
- Handling: keep excluded from training until the exact-file approval record is created privately with reviewer, review date, rights basis, and intended use. Do not treat this register entry as approval.


## Candidate 6 — Jon2 AI Original Arabic Dialogue Expansion Batch 02

- File: `ai_engine/training_data/original_dialogue_ar_batch_02.txt`
- Source: project-authored Arabic dialogue draft dated 2026-11-04. Its file header describes it as based on stable general knowledge and says no private conversations, copied web text, or third-party datasets were used; this declaration has not been independently verified.
- Raw file size: 38,276 Unicode characters; SHA-256: `bf675b91af1caff782a476e3249cadd86b7fdf20a63bf631a5a06a49aeeed6c2`.
- Intended role: candidate research material for factual uncertainty, learning, reasoning, everyday explanations, and safe assistance.
- Rights status: draft requiring repository-owner review and explicit acceptance of this exact file and intended training use; not legal advice or a guarantee of rights.
- Quality status: requires human review for accuracy, language, duplication, balance, and suitability.
- Status: **DRAFT / OWNER REVIEW REQUIRED / NOT APPROVED FOR TRAINING**.
- Handling: keep excluded from training until exact-file approval metadata is recorded in the private manifest.

## Candidate 7 — Jon2 AI Original Arabic Dialogue Expansion Batch 03

- File: `ai_engine/training_data/original_dialogue_ar_batch_03.txt`
- Source: project-authored Arabic dialogue draft. Its file header describes it as project-authored and says private conversations and copied third-party text were not used; this declaration has not been independently verified.
- Raw file size: 100,489 Unicode characters; SHA-256: `04702405388440877b2742135991007429d01d3ffe2533df6a4d931bb656a9bc`.
- Intended role: candidate research material for Arabic explanations, reasoning, language, writing, and multi-turn response patterns.
- Rights status: draft requiring repository-owner review and explicit acceptance of this exact file and intended training use; not legal advice or a guarantee of rights.
- Quality status: requires human review for factual accuracy, Arabic fluency, duplication, balance, and suitability.
- Status: **DRAFT / OWNER REVIEW REQUIRED / NOT APPROVED FOR TRAINING**.
- Handling: keep excluded from training until exact-file approval metadata is recorded in the private manifest.


## Verified first training experiment and exact-file owner approval — 2026-11-05

The repository's earlier candidate statuses above record their state before the owner approved the exact five project-authored files for a controlled research training run. The historical entries are retained rather than rewritten. The owner approval applied only to these exact files and hashes in the private approval manifest:

- `ai_engine/training_data/original_dialogue_ar.txt`
- `ai_engine/training_data/original_dialogue_ar_batch_01.txt`
- `ai_engine/training_data/original_dialogue_ar_batch_02.txt`
- `ai_engine/training_data/original_dialogue_ar_batch_03.txt`
- `ai_engine/training_data/original_seed_ar.txt`

A real CPU training run completed: [Jon2 Real CPU Training, run 42027297208](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42027297208). It used the private exact-file approval/hash gate and produced a private checkpoint. Recorded run metrics: 1,200 optimizer steps; 269,952 parameters; 289,120 Unicode characters; 185,697 training tokens; 20,679 validation tokens; best validation loss 3.6355 at step 900. The last resumable checkpoint was saved at step 1,200.

A 40-prompt held-out evaluation completed in [run 42028581017](https://github.com/jonkabeel-star/jon2-ai/actions/runs/42028581017). The checkpoint's generated Arabic answers were fragmented and not sufficiently understandable/coherent. Thus the training pipeline was exercised successfully, but the model did **not** pass the assistant-quality gate and is **not approved for chat release**.

Approval scope is limited to the five exact files above as they existed at approval time. It does not approve later edits, new batches, external datasets, Wikipedia, web-crawled text, or any other source. New or modified training material requires fresh explicit owner approval and rights review. Keep ArabicText-Large, HPLT, and Wikipedia sources NOT APPROVED as recorded above.

Operational decision: keep `JON2_CHAT_RELEASE_APPROVED` false. Do not describe the checkpoint as a functioning conversational assistant. Improve model and data quality before another controlled training run; do not repeat training unchanged merely to produce another checkpoint.


## Candidate 8 — Jon2 AI Original Arabic Dialogue Expansion Batch 04

- File: `ai_engine/training_data/original_dialogue_ar_batch_04.txt`
- Source: project-authored Arabic dialogue pack for clear Modern Standard Arabic explanations, coherence, uncertainty, reasoning, and step-by-step problem solving.
- Raw file size: 29,323 bytes; Unicode character count: 16,578; SHA-256: `6e4e8178d52f1f3b5019fbd7e516db0ac9eeef369ad8ee22b24c8648cb302928`.
- Owner review: explicitly approved for private experimental Jon2 research training on 2026-11-08.
- Intended use: `research_training` only. Public-model and commercial training are not authorized.
- Status: **APPROVED FOR PRIVATE EXPERIMENTAL RESEARCH TRAINING ONLY**.
- Handling: the approval applies only to the exact bytes and hash above. Any edit requires a new review and approval record.

## Candidate 9 — Structured Arabic Dialogue JSONL: Expanded

- File: `ai_engine/training_data/dialogue/jon2_dialogue_expanded.jsonl`
- Current size: 48 conversation records, 122 messages, 10,464 message-content characters.
- Format: structured user/assistant conversations, including multi-turn examples.
- Status: **NOT APPROVED** — exact-file human review and private approval manifest required before training.

## Candidate 10 — Structured Arabic Dialogue JSONL: Multi-turn Stage 2

- File: `ai_engine/training_data/dialogue/jon2_dialogue_multiturn_stage2.jsonl`
- Current size: 22 conversation records, 132 messages, 10,990 message-content characters.
- Format: structured multi-turn user/assistant conversations.
- Status: **NOT APPROVED** — exact-file human review and private approval manifest required before training.

## Candidate 11 — Structured Arabic Dialogue JSONL: Stage 2

- File: `ai_engine/training_data/dialogue/jon2_dialogue_stage2.jsonl`
- Current size: 117 conversation records, 234 messages, 18,744 message-content characters.
- Format: structured user/assistant question-and-answer conversations.
- Status: **NOT APPROVED** — exact-file human review and private approval manifest required before training.


## Candidate 12 — OpenITI Chunked Arabic Research Corpus

- Dataset ID: `mittagessen/openiti_chunked`.
- Hugging Face revision pinned for quarantine acquisition: `edb9823fb63b544a5cd7889b835a2f85146f031a`.
- Dataset card reports 10,222,980 chunks, approximately 17.9 GB download size and 38.0 GB dataset size.
- Hugging Face metadata declares CC0-1.0 for the converted dataset package.
- Upstream source: OpenITI release 2023.1.8. OpenITI's own documentation states that OpenITI releases are published under CC BY-NC-SA 4.0; its copyright FAQ separately explains its view that the historical underlying texts date to 1900 or earlier. These are distinct claims and must not be conflated with a blanket CC0 grant for the underlying corpus.
- Intended role: quarantined research and source-rights audit only.
- Status: **QUARANTINED / NOT APPROVED FOR JON2 TRAINING OR COMMERCIAL USE**.
- Reason: the upstream OpenITI release terms include a non-commercial restriction; the Hub package's CC0 label does not establish that the underlying source texts have been relicensed for commercial model training.
- Handling: use `ai_engine/download_arabic_candidate.py` only to download into a separate private quarantine folder. The tool pins the revision, records a manifest, and hard-codes both training and commercial eligibility to false. It refuses any destination inside `training_data`.
- Storage warning: approximately 17.9 GB compressed and 38.0 GB unpacked; standard 15 GB Drive storage is insufficient.
- Next requirement: resolve source-level rights and intended use with OpenITI / rights holders. If commercial rights cannot be established, permanently exclude this dataset from Jon2's commercial training corpus.
