# Cloudflare to private Jon2 runtime bridge

The Worker is an edge gateway only. It does not load PyTorch or store model weights.
This bridge forwards requests to the separately hosted Jon2 FastAPI service.

## Required Worker configuration

Only configure these values after a real private Jon2 runtime has been deployed and
its HTTPS `/v1/health` endpoint has been checked:

- `JON2_RUNTIME_URL`: HTTPS base URL of the private FastAPI service, without a trailing slash.
- `JON2_RUNTIME_TOKEN`: secret value of at least 32 characters. Store it as a Worker secret, never in source code, Pages, or browser JavaScript.

The Worker adds the Bearer token itself. The browser must never receive the runtime token.

## Routes

- `GET /api/health/live`: checks the edge Worker only.
- `GET /api/health`: proxies to private runtime `GET /v1/health` when configured; otherwise reports runtime not configured.
- `POST /api/chat`: validates the public request and proxies a versioned request to `POST /v1/chat`.
- If runtime configuration is missing or the upstream is unavailable, chat fails closed. There is no generated/fallback reply.

## Public chat request shape

```json
{
  "message": "مرحبا",
  "history": [],
  "session_id": null
}
```

The Worker adds `contract_version: "1"` and the private Authorization header.

## Safety and deployment gates

- This change does not deploy the Worker or change Cloudflare production.
- Keep `JON2_CHAT_RELEASE_APPROVED=false` until the exact checkpoint passes inference tests and human Arabic quality review.
- Do not upload `.pt` checkpoints, datasets, approval manifests, or credentials to the Git repository.
- The current repository Docker entrypoint attempts to retrieve a private checkpoint through Kaggle when no checkpoint file is mounted. This must be replaced or bypassed with an owner-approved private checkpoint delivery method before runtime deployment; do not configure a Kaggle token if the project is staying off Kaggle.
- Cloudflare Workers do not host PyTorch inference. A separate runtime with sufficient memory and compute is still required.
