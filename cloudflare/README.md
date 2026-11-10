# Jon2 Cloud

Jon2's public chat API runs on Cloudflare Workers with a Workers AI binding.

## Endpoints

- `GET /` and `GET /api/health/live`: liveness.
- `GET /api/health`: API and AI-binding configuration status. A successful health response does not replace a real inference test.
- `POST /api/chat`: sends a bounded Arabic-first conversation to the configured Qwen model and returns a real model response.
- `OPTIONS`: CORS preflight for the Jon2 GitHub Pages origin and local development.

## Model and free allocation

- Model: `@cf/qwen/qwen3.8-27b` through Cloudflare Workers AI.
- Workers Free includes 10,000 Neurons per day, resetting at 00:00 UTC. On Workers Free, requests fail after the allocation is exhausted. On Workers Paid, usage above the free allocation is billable. This repository does not configure a paid fallback or change the Cloudflare account plan; keep the account on Workers Free if you do not want AI overage charges.
- The model is hosted by Cloudflare. It is not the separately trained Jon2 checkpoint. This is a temporary real-model chat integration while the independent Jon2 model is prepared.

## Cloudflare setup

- Deploy from the repository root using the root `wrangler.toml`, whose entry point is `cloudflare/worker.js`.
- The root configuration declares the Workers AI binding named `AI`. The Cloudflare Worker must be deployed with that binding enabled.
- If deploying with Wrangler from inside the `cloudflare/` directory instead, its local `wrangler.toml` points to `worker.js` and declares the same `AI` binding.
- A GitHub-connected Cloudflare deployment should use the repository root as its root directory and the root Wrangler configuration.
- Do not put API tokens, account secrets, or model weights in this repository. The Worker does not require a public API token for the binding.

## Safety and limits

- Only the Jon2 GitHub Pages origin and the listed local development origins are accepted by browser CORS.
- User messages are limited to 2,000 characters.
- Conversation history is limited to the last 6 messages, with each history message truncated to 1,200 characters.
- Generated replies are capped at 384 tokens.
- A small in-memory per-isolate request guard allows at most 6 requests per IP per minute in each live isolate. It is best-effort only, not a globally consistent rate limiter.
- Cloudflare enforces the daily AI allocation at the account level. Monitor actual Neuron usage in the Cloudflare dashboard; the Worker cannot read or display an exact remaining-Neurons balance.
- The public health endpoint explains the quota and paid-plan billing distinction. Health reports that the binding is configured; only a successful `POST /api/chat` proves inference is working.
- User messages are not intentionally logged by this Worker.

## Deployment notes

The active Worker uses the JavaScript Workers runtime and Workers AI binding. `cloudflare/worker.py` is a legacy health-only Python reference and is not the configured entry point in either Wrangler configuration.
