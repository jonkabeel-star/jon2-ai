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
