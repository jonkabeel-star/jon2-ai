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

## Versioned Python runtime contract

`src/contracts.ts` defines the version 1 JSON contract shared by the TypeScript edge layer and a future approved Python runtime:

- `api_version: "1"` identifies the wire format.
- Chat requests contain a non-empty `message`, optional role-tagged `history`, and optional `request_id`.
- Health and chat success/error response types are defined explicitly.
- Incoming request validation limits message/history sizes and rejects unsupported roles or API versions.
- Runtime transport failures are normalized into safe timeout, authorization, or unavailable errors.

This is a contract and validation layer only. No upstream URL, runtime credential, model selection, or network forwarding is configured. The existing preview `POST /api/chat` remains HTTP 503 until an approved real runtime is available. Do not add secrets to source control.
