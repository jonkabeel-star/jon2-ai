# Jon2 AI TypeScript Worker Preview

This is a parallel TypeScript implementation for testing. It is deliberately separate from the production Python Worker.

## Safety

- Do not deploy this preview as production until parity tests pass and the owner approves the switch.
- The chat endpoint intentionally returns HTTP 503 while no real, approved model runtime is connected.
- No model weights, API keys, or private tokens belong in this directory.
- This Worker is an edge gateway only; it does not run PyTorch or load model checkpoints.

## Routes

- GET /api/health/live
- GET /api/health
- POST /api/chat (returns model_runtime_not_connected / HTTP 503)
- OPTIONS for CORS preflight

## Local preview

Use a supported Node.js LTS release and Wrangler from the project tooling:

1. Install the Wrangler CLI in a local development environment.
2. Run Wrangler in this directory with the preview config.
3. Check /api/health and verify that /api/chat returns HTTP 503 until a real model runtime is connected.

The root production wrangler.toml remains unchanged.
