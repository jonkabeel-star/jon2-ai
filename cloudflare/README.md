# Jon2 Cloud

Jon2's public chat API runs on Cloudflare Workers with a Workers AI binding.

## Endpoints

- `GET /` and `GET /api/health/live`: liveness.
- `GET /api/health`: API and AI-binding configuration status. A successful health response does not replace a real inference test.
- `POST /api/chat`: sends a bounded Arabic-first conversation to the configured Qwen model and returns a real model response.
- `OPTIONS`: CORS preflight for the Jon2 GitHub Pages origin and local development.

## Model and free allocation

- Model: `@cf/qwen/qwen3.8-27b` through Cloudflare Workers AI.
- Workers AI Free currently includes 10,000 Neurons per day. Requests fail after the daily free allocation is exhausted; no automatic paid upgrade is configured by this repository.
- The model is hosted by Cloudflare. It is not the separately trained Jon2 GGUF checkpoint. This is a temporary real-model chat integration while the independent Jon2 model is prepared.

## Cloudflare setup

The repository's `wrangler.toml` declares the Workers AI binding named `AI`. The Worker must be deployed with that binding enabled. If the Cloudflare dashboard uses a GitHub-connected deployment, ensure the project builds from the repository root and uses the root `wrangler.toml`.

Do not put API tokens, account secrets, or model weights in this repository. The Worker does not require a public API token for the binding.

## Safety and limits

- Only the Jon2 GitHub Pages origin and the listed local development origins are accepted by browser CORS.
- Request messages are limited to 2,000 characters; history is limited to the last 8 messages; generated replies are capped at 500 tokens.
- A small in-memory per-isolate request guard is best-effort only, not a globally consistent rate limiter.
- The Cloudflare daily AI free allocation is the hard usage boundary. Monitor usage in the Cloudflare dashboard.
- Health reports that the binding is configured; only a successful `POST /api/chat` proves inference is working.
- User messages are not intentionally logged by this Worker.

## Deployment notes

The Worker uses the JavaScript Workers runtime and Workers AI binding. The previous Python health-only Worker remains in `cloudflare/worker.py` for reference but is no longer the configured entry point.
