# Jon2 Arabic corpus preparation

**Status: builder implemented; the approved source manifest is currently empty, so no new corpus can be built from it.**

## Non-negotiable data rules

- No Wikipedia or Wikimedia-derived data.
- No CC BY-SA, unknown, missing, or merely assumed training rights.
- A public URL or permissive software license is not proof of permission to train on the data.
- Each dataset/version needs source-level provenance, explicit model-training permission, documentary rights evidence, a pinned version, a SHA-256 hash, and human approval.
- No scraping, downloading, or synthetic data generation is performed by the builder.
- Do not add third-party sources until their exact rights evidence has been reviewed and approved.

## Accepted source format

The existing approved_sources.json is the authoritative manifest. Each approved source record must satisfy rights_gate.py and include an additional local_path relative to a private data root.

Supported local files:
- UTF-8 .txt: one non-empty document per line.
- UTF-8 .jsonl: one JSON object per line with a string text field.

The recorded content_hash_sha256 must match the exact local source bytes. The builder rejects symlinks, path traversal, unsupported extensions, malformed JSONL, changed source hashes, and unapproved rights records.

## Build

The builder has a command-line entry point. From the ai_engine directory, run it only after a human has reviewed and approved the exact source records and source bytes:

~~~bash
python -m data_rights.corpus_builder \
  --manifest data_rights/approved_sources.json \
  --data-root /secure/jon2-approved-sources \
  --output-dir /secure/jon2-corpus/run-001
~~~

The output directory must be outside both the private source directory and the Git repository. The builder creates:

- train.jsonl
- validation.jsonl

Each output is UTF-8 JSONL with exactly one JSON record per line and a final newline. Every record contains text, source_id, and the verified source-file SHA-256. Whole sources are assigned to one split to avoid source-level leakage; exact duplicate document text is removed globally across both splits.

The returned document counts describe retained records after exact-text deduplication. The rights_verified field means only that the local manifest checks and source hash checks passed. The builder does not fetch evidence URLs, independently establish ownership, or provide a legal opinion. A human reviewer remains responsible for the rights decision.

The builder prepares data only. It does not tokenize, train, create a checkpoint, approve a model, or publish a service. Keep the corpus private; do not commit it or put it in the public container image.

## Current project state

- approved_sources.json contains zero approved external sources.
- The separate owner-written seed-data approval workflow is not replaced by this manifest and must be checked independently before using those files.
- This builder prepares documents, not tokens. A tokenizer-training pipeline, deduplication beyond exact text, language/quality filters, contamination checks, and robust held-out evaluation are still required.
- A small approved corpus is not enough to train a useful 20B model from scratch. Never duplicate it to satisfy a token-count gate.
