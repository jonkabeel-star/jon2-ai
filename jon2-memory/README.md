# Jon2 Memory

Standalone durable conversation-memory API for Jon2 AI. It stores and retrieves messages; it does not run a language model or generate AI answers.

## Architecture
- Cloudflare Worker: authenticated HTTPS API.
- Cloudflare D1: durable SQLite-compatible database.
- schema.sql: message and memory-note tables with owner/session indexes.
- The browser must never receive the memory API secret. Only a trusted Jon2 backend should call this service.

## Endpoints
- GET /health — database readiness, no private data.
- POST /v1/messages — save one message. JSON: owner_id, session_id, role, content, optional metadata.
- GET /v1/context?owner_id=...&session_id=...&limit=20 — retrieve recent messages.
- POST /v1/search — JSON: owner_id, query, optional limit; simple lexical search.
- DELETE /v1/messages — JSON: owner_id, session_id; delete one session's messages.

All routes except health require Authorization: Bearer <JON2_MEMORY_API_KEY>.

## Deployment
1. In Cloudflare Dashboard, create a D1 database named jon2-memory.
2. Open its Console and run the full schema.sql.
3. Create a Worker named jon2-memory and upload worker.js, or deploy this folder with Wrangler.
4. Add a D1 binding named MEMORY_DB pointing to jon2-memory.
5. Add Worker secret JON2_MEMORY_API_KEY with a long random value. Never put this secret in website JavaScript.
6. Set ALLOWED_ORIGINS to exact trusted website origins. Prefer server-to-server calls.
7. Replace the placeholder database ID in wrangler.toml if deploying with Wrangler.

## Free-tier boundaries
Cloudflare's published Workers Free/D1 limits currently include 5 GB total D1 storage per account, 5 million rows read per day, 100,000 rows written per day, and a 500 MB maximum size per D1 database on Free. Free Workers also have request and CPU limits. If a daily D1 quota is exceeded, queries fail until reset; stored data is not deleted. Limits can change.

## Security and integration
- Generate an unpredictable owner_id for each authenticated Jon2 user on the trusted backend. Never trust owner_id supplied by an unauthenticated browser.
- Do not expose the shared API key in frontend code.
- Add real user authentication, per-user quotas/rate limiting, account export/deletion, and abuse monitoring in the Jon2 gateway before public multi-user launch.
- CORS is not authentication.
- Search is lexical, not semantic/vector memory. Embeddings can be added later without changing message durability.
- This service is not connected to the live Jon2 website yet. Do not remove the current chat route until integration and isolation tests pass.
