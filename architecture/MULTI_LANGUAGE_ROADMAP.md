# Jon2 AI — Multi-Language Architecture Roadmap

Status: architecture plan only. This document does not switch the production Worker or change model behavior.

## Goals

- Keep the existing Cloudflare site and API working.
- Keep the AI model runtime and model weights separate from the hosting provider.
- Prefer free tiers, with no paid upgrade or billing activation without owner approval.
- Make every runtime replaceable through a documented HTTP/JSON contract.
- Preserve existing Python code, evaluation tests, data-rights gates, and checkpoints.

## Language responsibilities

| Technology | Responsibility | Deployment target |
|---|---|---|
| TypeScript (current Node.js LTS) | Cloudflare edge API, request validation, CORS, routing, frontend integration | Cloudflare Workers |
| Python 3 | AI inference adapter, tokenization, model loading, evaluation, training tools | Separate replaceable compute runtime |
| SQL | Durable conversation metadata and account data | Cloudflare D1 or another portable SQL database |
| Rust | Optional high-safety native/WASM components only when profiling proves a need | WASM-compatible edge component or portable server |
| C++ | Optional optimized kernels only when profiling proves a need | Model runtime build, not Cloudflare Worker |
| Go | Deferred; add only if a separate orchestration service becomes necessary | Portable server runtime |

Do not add languages just to increase the count. More languages increase maintenance, build time, and security surface. TypeScript + Python + SQL are the first practical stack. Rust and C++ are later, evidence-driven additions. Go is not required for the first production milestone.

## Service boundaries

1. **Web frontend** — existing HTML/CSS/JavaScript site. Keep it static and provider-independent.
2. **Edge gateway** — Cloudflare Worker. It authenticates requests, validates payloads, applies limits, and forwards approved requests to the configured model runtime. It must not contain model weights.
3. **Model runtime** — Python service exposing a versioned HTTP API. It loads a locally available, rights-approved checkpoint. It reports unavailable when no approved model is loaded; it must never return fabricated AI responses.
4. **Data layer** — SQL schema and migrations remain portable. Secrets are stored only in provider secret storage, never in GitHub or browser JavaScript.
5. **Model artifacts** — weights are stored separately from source code, with checksums, license/rights records, and backup instructions.

## Versioned runtime contract

Base path: /v1

- GET /health returns service status, model readiness, model identifier, and runtime version.
- POST /chat accepts a JSON object containing a message and optional conversation_id.
- Successful chat returns a reply, conversation_id, and model identifier.
- If no approved model is loaded, return HTTP 503 with a stable error code such as model_not_ready.
- Enforce request size limits, timeouts, authentication between gateway and runtime, and rate limits.
- Never expose internal tokens, filesystem paths, stack traces, or private model locations to the browser.

## Migration plan

### Phase 1 — Safe foundation
- Keep the current production Python Worker unchanged.
- Add this architecture record and maintain a clean separation between frontend, gateway, model runtime, database, and model artifacts.
- Record current endpoint behavior before any migration.

### Phase 2 — TypeScript gateway in parallel
- Build a separate TypeScript Worker implementation with the same health and error behavior.
- Run tests against both implementations.
- Do not change the production wrangler.toml entry point until parity tests pass and the owner approves deployment.

### Phase 3 — Portable Python runtime
- Adapt the existing Python engine behind /v1/health and /v1/chat.
- Keep model loading disabled unless a checkpoint passes the project's data-rights review and resource checks.
- Keep model weights out of the Git repository.

### Phase 4 — Storage and portability
- Use migrations for SQL changes.
- Keep export/backup procedures documented.
- Avoid provider-specific APIs in the model engine; isolate them behind adapters.

### Phase 5 — Optional native acceleration
- Add Rust/WASM or C++ only after profiling identifies a real bottleneck and the target host supports it.
- Add Go only if the project later needs a distinct orchestration service.

## Non-negotiable safeguards

- No paid service, billing activation, or automatic paid fallback without explicit owner approval.
- No model download, training, or deployment before data-rights approval.
- No deletion or replacement of existing Python engine files as part of the language migration.
- No production switch until tests pass and rollback is documented.
- Free-tier quotas and uptime are not guaranteed; the system must fail safely when a free quota is exhausted.
