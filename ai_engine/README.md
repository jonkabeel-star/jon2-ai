# Jon2 AI — Original Model API

This API serves the **project-owned Jon2 Transformer**. It does not load Qwen,
GPT, another pretrained model, or a hosted AI API.

## Current model status

- The model architecture and training code are in `jon2_core.py`.
- The chat runtime loads only a trained Jon2 checkpoint.
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

## Train the original model

Training is deliberately separate from serving. Add enough high-quality,
clean UTF-8 text that Jon2 owns or is explicitly licensed to use for model
training. Record every source and license in `DATASET_REGISTER.md`.

From the repository root:

```bash
python ai_engine/jon2_core.py --data ai_engine/training_data --output ai_engine/checkpoints/jon2-small.pt
```

The default training settings are only a prototype. A small run on the current
seed corpus will not create a capable assistant. Training quality must be
measured on held-out Arabic questions before the checkpoint is deployed.

## Evaluate a trained checkpoint

After training, run the Arabic smoke evaluation:

```bash
python ai_engine/evaluate_model.py --checkpoint ai_engine/checkpoints/jon2-small.pt --output ai_engine/evaluation/first-review.json
```

The script tests a fixed set of Arabic prompts covering explanation, arithmetic,
story coherence, clarification, time-sensitive claims, and basic concepts. It
prints the answers and can save a JSON review report. A human must judge each
answer for correctness, relevance, Arabic fluency, repetition, and whether the
model admits uncertainty. Passing this smoke test does not certify safety or
production quality.

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
