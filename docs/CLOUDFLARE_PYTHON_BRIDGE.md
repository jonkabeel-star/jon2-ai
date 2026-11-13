# Jon2 Cloudflare Pages ↔ Python runtime bridge

The public website uses Cloudflare Pages Functions as a same-origin gateway to Jon2's own FastAPI runtime. It never calls Workers AI, OpenAI, Gemini, or another hosted model.

## 1. Python runtime

Deploy the repository's root `render.yaml` on Render (or another HTTPS Docker host with enough RAM, CPU, and disk for CPU PyTorch).

Set these private values in the Python service:
- `KAGGLE_API_TOKEN`: a valid Kaggle token with access to `jon2kabeel/jon2-private-model-checkpoint`.
- `JON2_RUNTIME_TOKEN`: a random secret of at least 32 characters. Keep it private.
- `JON2_CHAT_RELEASE_APPROVED=false`.
- `JON2_INFERENCE_TESTED=false`.
- `JON2_QUALITY_REVIEW_PASSED=false`.

The Render blueprint now sets `JON2_PRELOAD_MODEL=true`. On startup, the entrypoint first attempts to download the existing private checkpoint if it is missing; the Python startup hook then loads it. This does not train, rewrite, or release the checkpoint. If the selected host cannot fit CPU PyTorch and the model in memory, move to a host with more memory rather than bypassing the startup or release gates.

Verify:
- `https://YOUR-PYTHON-HOST/api/health/live` returns HTTP 200.
- `/api/health` reports `checkpoint_configured=true` and, after successful preload, `model_loaded=true`.
- `/v1/health` reports `api_ready=true` only when the runtime token is configured.

## 2. Cloudflare Pages Functions gateway

The repository includes `functions/api/[[path]].js`. Cloudflare Pages deploys it as the same-origin `/api/*` gateway and reuses the reviewed proxy in `cloudflare/worker.js`.

In Cloudflare Dashboard → Workers & Pages → `jon2-ai` → Settings → Variables and Secrets, add for Production:
- Variable `JON2_RUNTIME_URL` = the Python service origin, e.g. `https://YOUR-PYTHON-HOST` (no `/v1` suffix).
- Secret `JON2_RUNTIME_TOKEN` = exactly the same value as the Python service's `JON2_RUNTIME_TOKEN`.

Redeploy the Pages project after setting the values. The secret is added server-side and is never sent to the browser.

The frontend config points to `https://jon2-ai.pages.dev`. If Cloudflare shows a different Pages production hostname, update `jon2-config.js` to that exact HTTPS origin. Do not guess a `workers.dev` hostname.

## 3. Chat release safety

The public chat gate remains closed until all conditions are true: the exact checkpoint exists and is loaded, inference tests passed, human Arabic quality review passed, and the owner explicitly approves release. Do not change these flags merely to make the status green. A loaded model is not proof of useful Arabic answers.

## 4. Verification sequence

1. Python liveness returns HTTP 200.
2. Python health confirms checkpoint configured and loaded.
3. Pages `https://jon2-ai.pages.dev/api/health/live` returns gateway liveness.
4. Pages `/api/health` reports `runtime_configured=true` and reflects Python's real `chat_ready` state.
5. Only after held-out Arabic tests and human review should public chat be approved.

GitHub cannot enter secrets into the owner's Render or Cloudflare accounts, read private Kaggle credentials, or prove deployment without access to those dashboards. Never commit secrets, model weights, or private training data.
