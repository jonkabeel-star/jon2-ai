# Arabic Wikipedia corpus import — quarantine only

This workflow gives Jon2 a reproducible way to collect a larger Arabic text
candidate without changing the approved training corpus or private weights.

## Selected source

- Dataset: [Wikipedia Monthly](https://huggingface.co/datasets/omarkamali/wikipedia-monthly)
- Maintainer: Omar Kamali / Omneity Labs
- Pinned configurations: `20260301.ar` (Arabic) and `20260301.arz` (Egyptian Arabic)
- Declared license: **CC-BY-SA-4.0**
- Attribution: Wikipedia Monthly, maintained by Omar Kamali and Omneity Labs,
  built from Wikimedia dumps; CC-BY-SA-4.0.
- Dataset card reports approximately 1.3M Arabic articles and 1.6M Egyptian
  Arabic articles in the March 2026 export. The loader uses streaming and a
  configurable per-language character cap, rather than downloading the full
  multi-language archive.

The license permits commercial reuse subject to its attribution and share-alike
conditions. That does not remove the need to review the dataset's content,
privacy risks, source provenance, and the implications of training/distributing
a model on adapted material. Keep this source quarantined until those questions
are reviewed for Jon2's intended use.

## Run from Kaggle

The Jon2 GitHub repository is private. Do not use an anonymous `git clone`
command or paste a GitHub password/token into a notebook.

1. Make the importer file available to the Kaggle notebook using Kaggle's
   authorized GitHub integration, if connected, or upload the file from a
   signed-in GitHub session.
2. In a Kaggle code cell, install the optional dataset reader:

```python
!pip -q install datasets
```

3. Run the script from the path where it was made available. For example:

```python
!python /kaggle/working/prepare_arabic_corpus.py --output-dir /kaggle/working/jon2-arabic-quarantine
```

4. Download the quarantine output from Kaggle for human review.

If Kaggle cannot reach Hugging Face or package installation fails, stop and
report the exact error. Do not substitute another dataset or bypass source
checks. Never expose a GitHub or Hugging Face access token in notebook output.

## Safety guarantees

- Downloads only the two pinned language configurations.
- Streams rows and applies a per-language character cap.
- Normalizes Unicode and whitespace, rejects very short/non-Arabic/URL-bearing
  articles, and removes exact duplicate articles.
- Writes text and SHA-256 provenance into a separate quarantine folder.
- Marks the manifest `PENDING_HUMAN_LEGAL_AND_CONTENT_REVIEW`.
- Does **not** write into `ai_engine/training_data`, modify
  `source_approvals.json`, start training, or change any checkpoint.
- The output is not automatically eligible for training.

The 10-million-character default cap per language is a collection limit, not a
claim that the resulting corpus is sufficient to train a conversational model.
After import, run a read-only audit and preflight; only a separately approved
source manifest may be used for training.
