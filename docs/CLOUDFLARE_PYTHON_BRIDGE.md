# Jon2 Cloudflare ↔ Python runtime bridge

This bridge connects the existing Cloudflare Worker to the project's own FastAPI runtime. It never calls Workers AI, OpenAI, Gemini, or another hosted model.

## Required services

1. Deploy the Python API from the repository's root `render.yaml` (or another HTTPS host that can run the Dockerfile and has enough RAM for PyTorch).
2. In the Python service, set these private environment values:
   - `KAGGLE_API_TOKEN`: a valid Kaggle API token for the private checkpoint dataset `jon2kabeel/jon2-private-model-checkpoint`.
   - `JON2_RUNTIME_TOKEN`: a random secret of at least 32 characters. Keep it private.
   - `JON2_CHAT_RELEASE_APPROVED=false` initially.
   - `JON2_EXPERIMENTAL_CHAT=false` initially.
3. Confirm the Python service responds at `https://YOUR-PYTHON-HOST/api/health/live` and inspect `/api/health`. The entrypoint downloads the private checkpoint only when the Kaggle token is valid and the service can write its model directory. It does not train or modify the checkpoint.
4. In Cloudflare Worker settings, set:
   - Variable `JON2_RUNTIME_URL` = the Python service origin, e.g. `https://YOUR-PYTHON-HOST` (no `/v1` suffix).
   - Secret `JON2_RUNTIME_TOKEN` = the exact same value as the Python service's `JON2_RUNTIME_TOKEN`.
5. Deploy `cloudflare/worker.js`. The Worker proxies `GET /api/health` to Python `GET /v1/health` and `POST /api/chat` to Python `POST /v1/chat`. The secret is added server-side and is never sent to the browser.
6. After deployment, set `window.JON2_API_BASE_URL` in the public `jon2-config.js` to the exact HTTPS Worker origin shown in the Cloudflare dashboard. Do not guess the `workers.dev` hostname. The current blank value intentionally prevents the public site from calling an unknown endpoint.

## Chat release safety

- The default remains closed: `JON2_CHAT_RELEASE_APPROVED=false` and `JON2_EXPERIMENTAL_CHAT=false`.
- The public release gate requires a configured checkpoint, loaded model, an inference-test flag, a human quality-review flag, and explicit release approval.
- An owner may explicitly set `JON2_EXPERIMENTAL_CHAT=true` on the private Python service to allow clearly experimental replies after the checkpoint is available. The first experimental chat request lazily loads the original checkpoint. This does not mark inference as tested, pass human review, or approve public release.
- Do not enable experimental mode for anonymous public traffic until the owner has accepted that the existing small model may produce incoherent Arabic. Do not set the public release flags just to make the status green.
- A health-only deployment is not proof that PyTorch inference fits the host. Render Free has very limited RAM/CPU and may not be able to load the runtime. Measure actual checkpoint loading and inference on the selected host.

## Verification sequence

1. Python `/api/health/live` returns HTTP 200.
2. Python `/api/health` reports `checkpoint_configured=true`; after a real load it reports `model_loaded=true`.
3. Python `/v1/health` reports `api_ready=true` only when the runtime token is configured.
4. Cloudflare `/api/health` reports `runtime_configured=true` and reflects Python's real model/chat status.
5. Send a short Arabic test through the website only after the owner chooses whether to keep chat closed or enable experimental mode. Record the exact response and review it; never infer language quality from HTTP 200 alone.

## What this repository cannot do on its own

GitHub cannot create/authorize the owner's Render or Cloudflare services, reveal their service URLs, or enter private Kaggle/Cloudflare secrets. Those account-controlled steps must be completed in the hosting dashboards. No secret, checkpoint, or private dataset belongs in Git.
