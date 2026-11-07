# Jon2 Runtime API Contract v1

This contract defines the boundary between the TypeScript edge gateway and the independent Python model runtime.

## Rules

- Contract version: `1`.
- Runtime health must explicitly report API readiness and model readiness.
- A healthy API does not imply that a model is loaded.
- Chat success requires a non-empty `reply` returned by the real runtime.
- Runtime errors must be structured and must not be converted into fabricated replies.
- The gateway must use a configured private runtime URL and authentication secret.
- Runtime calls must have a bounded timeout and must never expose secrets to the browser.
- The edge gateway must return an unavailable response when the runtime is missing, unhealthy, unauthorized, times out, or returns an invalid contract.
- No model provider, checkpoint, or external inference API is selected by this contract.

## Python runtime implementation

- `GET /v1/health` reports contract version, API readiness, model readiness, and model status.
- `POST /v1/chat` accepts the versioned request and returns a versioned reply or structured error.
- Chat requires `Authorization: Bearer <token>`.
- Configure `JON2_RUNTIME_TOKEN` as a secret of at least 32 characters in the Python runtime environment.
- The token is compared in constant time and is never returned by the API.
- The CORS policy permits the Authorization header for approved site origins.
- The existing human release gate and checkpoint checks remain mandatory; authentication does not approve a model.
- Health reports `api_ready: false` until the runtime secret is configured.

## Health response

```json
{
  "contract_version": "1",
  "project": "Jon2 AI",
  "status": "online",
  "api_ready": false,
  "model_ready": false,
  "model_status": "checkpoint_missing"
}
```

## Chat request

```json
{
  "contract_version": "1",
  "message": "مرحبا",
  "history": [],
  "session_id": "optional-session-id"
}
```

## Successful chat response

```json
{
  "contract_version": "1",
  "project": "Jon2 AI",
  "reply": "..."
}
```

This contract and its validators do not claim that a runtime is deployed or that a model is approved.
