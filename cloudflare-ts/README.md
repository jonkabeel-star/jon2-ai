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


## Optional authenticated Python runtime bridge (preview only)

The TypeScript preview can forward chat requests to the existing Jon2 FastAPI
runtime. Configure these Cloudflare Worker bindings in the preview environment:

- `JON2_RUNTIME_URL`: HTTPS origin of the separately hosted Python API (for example, `https://your-private-runtime.example`; do not include `/v1/chat`).
- `JON2_RUNTIME_TOKEN`: a secret of at least 32 characters, matching the Python server's `JON2_RUNTIME_TOKEN`.

The gateway calls `GET /v1/health` for readiness and sends authenticated
`POST /v1/chat` requests using the Python runtime's `contract_version: "1"`
schema. The token must be stored as a Cloudflare secret, never in GitHub,
source files, frontend JavaScript, or a normal non-secret variable.

The Python service still requires all of the following before it can answer:
a deployed HTTPS runtime, the approved original Jon2 checkpoint at
`JON2_CHECKPOINT`, `JON2_CHAT_RELEASE_APPROVED=true` only after human
review of that exact checkpoint, and the same private token in
`JON2_RUNTIME_TOKEN`. The repository's documented current checkpoint
previously failed practical Arabic conversation review. Do not approve or expose
that checkpoint merely to make the connection return success.

This is a preview bridge only. It is not deployed and does not change the
production Worker. A running, reachable Python host and owner-configured
Cloudflare bindings are still required for a real end-to-end connection.

- In `/api/health`, `api_ready` describes the edge gateway itself; `runtime_api_ready` describes whether the configured Python service is reachable and authenticated/configured. `model_ready` remains the separate model-release readiness signal.
