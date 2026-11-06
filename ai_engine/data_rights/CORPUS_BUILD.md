# Jon2 Arabic corpus preparation

**Status: builder implemented; the approved source manifest is currently empty, so no new corpus can be built yet.**

## Non-negotiable data rules

- No Wikipedia or Wikimedia-derived data.
- No CC BY-SA, unknown, missing, or merely assumed training rights.
- A public URL or permissive software license is not proof of permission to train on the data.
- Each dataset/version needs source-level provenance, explicit model-training permission, documentary rights evidence, a pinned version, a SHA-256 hash, and human approval.
- No scraping, downloading, or synthetic data generation is performed by the builder.
- Do not add third-party sources until their exact rights evidence has been reviewed and approved.

## Accepted source format

The existing `approved_sources.json` is the authoritative manifest. Each approved source record must satisfy `rights_gate.py` and include an additional `local_path` relative to a private data root.

Supported local files:
- UTF-8 `.txt`: one non-empty paragraph per line.
- UTF-8 `.jsonl`: one JSON object per line with a string `text` field.

The recorded `content_hash_sha256` must match the exact local source bytes. The builder rejects symlinks, path traversal, unsupported extensions, malformed JSONL, changed source hashes, and unapproved rights records.

## Build

Run from the `ai_engine` directory after an owner has placed the approved files in a private data directory and updated the manifest with reviewed evidence:

```bash
python -m data_rights.corpus_builder \
  --manifest data_rights/approved_sources.json \
  --data-root /secure/jon2-approved-sources \
  --output-dir /secure/jon2-corpus/run-001
```

The module currently exposes a Python function rather than a command-line interface; use this equivalent call from a trusted Python environment:

```python
from data_rights.corpus_builder import build_corpus

report = build_corpus(
    "data_rights/approved_sources.json",
    "/secure/jon2-approved-sources",
    "/secure/jon2-corpus/run-001",
)
print(report)
```

The output directory must be outside the Git repository and separate from the source directory. It contains `train.jsonl` and `validation.jsonl`, plus SHA-256 values in the returned report. Keep the corpus private; do not commit it or put it in the public container image.

## Current project state

- `approved_sources.json` contains zero approved external sources.
- The existing owner-approved Jon2 seed files may only be used if the exact five approved files are available, their bytes are verified, and the owner confirms their hashes/locations. Do not silently substitute similarly named files.
- This builder prepares documents, not tokens. A tokenizer-training pipeline, deduplication, language/quality filters, contamination checks, and robust held-out evaluation are still required.
- A small approved corpus is not enough to train a useful 20B model from scratch. Never duplicate it to satisfy a token-count gate.
