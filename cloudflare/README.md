# Jon2 Cloudflare Edge Gateway

The currently configured production entry point is `cloudflare/worker.js`. It is a **health-only edge gateway**, not a language model runtime.

## Current behavior

- `GET /` and `GET /api/health/live`: report that the edge gateway process is alive.
- `GET /api/health`: reports edge API liveness separately from original-model readiness.
- `POST /api/chat`: deliberately returns HTTP 503 with `model_runtime_not_connected`.
- `OPTIONS`: handles CORS preflight for the published GitHub Pages origin and local development.

The worker does not load a checkpoint, run inference, call Workers AI, or forward requests to another model provider. A successful health response proves only that the edge gateway responds. It does not prove that Jon2 can generate an answer.

## Original Jon2 runtime requirements

The independent Python/FastAPI service must be deployed separately with the exact private Jon2 checkpoint. Before any chat route can be enabled, that checkpoint must pass inference tests, held-out Arabic evaluation, and human quality review. The API release flags must remain disabled until those checks and the explicit release decision are complete.

The repository contains a separate TypeScript bridge preview under `cloudflare-ts/`. It is not the configured production entry point and is not deployed by the root Wrangler configuration. Its optional authenticated Python-runtime forwarding requires a real HTTPS Python host plus the `JON2_RUNTIME_URL` and `JON2_RUNTIME_TOKEN` Cloudflare bindings. Do not configure those values until a private runtime actually exists and has passed the required review.

## Deployment

Deploy from the repository root using `wrangler.toml`, whose entry point is `cloudflare/worker.js`. The production worker does not need a Workers AI binding. The local `cloudflare/wrangler.toml` points to the same health-only worker when deploying from that directory.

Do not put API tokens, account secrets, training data, or model weights in this repository. Store runtime credentials only as provider-managed secrets.

## CORS and fail-closed behavior

- Browser requests are accepted only from the origins explicitly listed in `cloudflare/worker.js`.
- Unapproved browser origins receive HTTP 403.
- Chat remains HTTP 503 until a separately deployed and approved original Jon2 runtime is connected.
- The worker intentionally does not use a hosted model as a fallback.

`cloudflare/worker.py` is a legacy reference and is not the configured production entry point.
