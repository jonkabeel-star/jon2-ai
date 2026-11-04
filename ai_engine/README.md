# Jon2 AI — Original Model API

This API serves the **project-owned Jon2 Transformer**. It does not load Qwen,
GPT, another pretrained model, or a hosted AI API.

## Current model status

- The original Transformer architecture and backward-compatible checkpoint loader are in `jon2_core.py`.
- New training runs use the project-trained byte-level BPE tokenizer in `tokenizer.py`. It has UTF-8 byte fallback for unseen Arabic, English, punctuation, and emoji; it does not provide pretrained knowledge.
- The chat runtime loads only a trained Jon2 checkpoint.
- Dialogue generation stops when it reaches the next `المستخدم:` turn marker, so a reply does not intentionally continue into the following training example.
- The repository's small original seed text is for pipeline checks only. It is
  not enough to train a useful general-purpose assistant.
- Until a checkpoint exists, `POST /api/chat` intentionally returns HTTP 503
  with a clear message. It does not generate fake answers.
- A successful `/api/health` response means the API is running; check
  `checkpoint_configured` and `model_loaded` before expecting chat to work.

## Local API start

From the repository root, install dependencies:

```bash
pip install -r requirements.txt
uvicorn main:app --app-dir ai_engine --host 0.0.0.0 --port 8000
```

The default checkpoint location is `ai_engine/checkpoints/jon2-small.pt`.
You can override it with the `JON2_CHECKPOINT` environment variable.

## Audit the training text first

Run the dependency-free data audit before training:

```bash
python ai_engine/audit_data.py
```

The audit reports file sizes, checks the alternating user/assistant format in
the original dialogue draft, and reports exact duplicate lines. A small corpus
is reported as a warning rather than silently padded with repeated text.
Passing this structural audit does **not** approve copyright, privacy, or
commercial-use rights; review `DATASET_REGISTER.md` separately.

Before adding data, follow `training_data/CONTRIBUTING.md`. It explains ownership, permission, privacy, quality, and formatting requirements.

## Train the original model

Training is deliberately separate from serving. Add enough high-quality,
clean UTF-8 text that Jon2 owns or is explicitly licensed to use for model
training. Record every source and license in `DATASET_REGISTER.md`.

From the repository root:

```bash
python ai_engine/train_jon2.py --data ai_engine/training_data --output ai_engine/checkpoints/jon2-small.pt --keep-last
```

The tokenizer is learned only from the supplied project-owned/licensed corpus. The default BPE vocabulary size is 512 and can be changed with `--tokenizer-vocab-size`. Byte-level fallback keeps unseen characters representable. Existing character-tokenizer checkpoints remain loadable, but new BPE checkpoints use a different vocabulary and must be trained from scratch.

The default training settings are only a prototype. A small run on the current
seed corpus will not create a capable assistant. Training quality must be
measured on held-out Arabic questions before the checkpoint is deployed.

When `--keep-last` is enabled, `jon2-last.pt` now stores model weights,
optimizer state, learning-rate scheduler state, AMP scaler state, Python and
PyTorch random-number-generator states, plus a SHA-256 fingerprint of the
training corpus. To resume the same run after an interruption, use the same
training arguments and add:

```bash
python ai_engine/train_jon2.py --data ai_engine/training_data --output ai_engine/checkpoints/jon2-small.pt --last-checkpoint ai_engine/checkpoints/jon2-last.pt --resume ai_engine/checkpoints/jon2-last.pt --keep-last
```

Resume validation rejects changed training text, tokenizer/model configuration,
or training-plan settings instead of silently continuing a different run.
Older checkpoints without complete resume metadata are accepted only through
the documented legacy fallback and cannot provide bit-for-bit exact resumption.

## Evaluate a trained checkpoint

The held-out Arabic prompt set is `evaluation/prompts_ar.jsonl`. It is JSONL,
not a `.txt` file, so the training corpus reader does not ingest it.

After a real checkpoint has been trained, run:

```bash
python ai_engine/evaluate_model.py --checkpoint ai_engine/checkpoints/jon2-small.pt --prompts ai_engine/evaluation/prompts_ar.jsonl --output ai_engine/evaluation/review-report.json
```

The evaluator generates answers and creates a review template with six blank
human-scoring dimensions for every prompt. It never assigns an automatic quality
verdict or marks the model approved. Review every answer using
`EVALUATION_RUBRIC.md`. No checkpoint currently exists, so this evaluation
cannot yet be run against a trained model.

## API endpoints

- `GET /` — API identity and status
- `GET /api/health` — checkpoint and model readiness
- `POST /api/chat` — generate a response from the trained Jon2 checkpoint
- `GET /docs` — interactive API documentation

Example request:

```json
{"message":"اشرح لي معنى الطاقة الشمسية"}
```

Never put private keys, credentials, or private training data in the public
repository. GitHub Pages hosts only the frontend; it cannot run this model.


## Collecting an attributed Arabic starter corpus

The Colab notebook now includes a collection step that calls the official Arabic Wikipedia MediaWiki API and aims to collect 130,000 Arabic characters. It writes `training_data/wikipedia_ar_cc_by_sa.txt` plus `training_data/wikipedia_ar_sources.json` with article titles and URLs for attribution. This collection runs in the user's Colab session; it is not downloaded or committed by GitHub Actions. Verify the final character count, page-specific notices, and source manifest before training. Wikipedia text is generally CC BY-SA 4.0; attribution and share-alike requirements apply, and commercial/model-weight distribution questions need separate review.


## Mandatory source approval gate

The trainer now refuses to start unless every `.txt` file under the selected data folder has an explicit matching approval record in a JSON manifest. The default private manifest path is `ai_engine/training_data/source_approvals.json`. The public `source_approvals.example.json` file is only a format example; it does not approve any source. Copy the example into private storage, replace it with truthful source-by-source review records, and keep the manifest and training corpus out of the public repository. Each record must use status `APPROVED`, identify a reviewer and review date, document the rights basis, and select the intended use. The manifest is an operational safeguard, not legal verification; a reviewer must actually inspect the evidence. Never mark a source approved just to bypass the gate.

Every approval record must also bind to the exact file version using `sha256` (the lowercase SHA-256 of the raw file bytes) and `character_count` (the exact UTF-8 character count). The gate recomputes both values and blocks training if a file changes after review. The all-zero hash in the public example is a placeholder and must be replaced with the actual fingerprint; the example is not directly usable as an approval.
The gate does not make the current starter text suitable for training. It remains pipeline-test material until the project owner reviews and approves it, and the corpus must still meet the configured size and quality requirements.
