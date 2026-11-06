# Jon2 Cloud

This is the first real Python edge API layer for Jon2, designed for Cloudflare Workers.

## Current endpoints

- `GET /` and `GET /api/health/live`: liveness response.
- `GET /api/health`: reports edge API status separately from model readiness.
- `POST /api/chat`: deliberately returns HTTP 503 until a genuine Jon2 model runtime is connected.
- `OPTIONS`: CORS preflight for the Jon2 GitHub Pages origin and local development.

## Important boundary

This Worker is an API edge layer, not a model host. Cloudflare Workers Free has strict per-request CPU and memory limits, so this Worker does not load PyTorch, Transformers, model checkpoints, or claim to run inference. The model remains unavailable until a separate compatible runtime is connected and passes review.

## Deployment

Use the Cloudflare Workers dashboard with the repository integration, set the project root/build configuration to this directory, and deploy the Python Worker using the current Cloudflare Python Workers workflow. Do not add secrets or model weights to this directory.

The Worker is not yet connected to the public Jon2 website. Do not change `jon2-config.js` until a real deployed Worker URL has been verified.
