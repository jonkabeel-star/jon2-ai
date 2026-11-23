# Jon2 Search API — Beacon Worker

This is the lightweight JavaScript edge deployment for the existing Jon2 website search contract.

## Endpoints
- `GET /` and `GET /api/health`: service health. Explicitly reports `chat_ready:false` and `model_ready:false`.
- `POST /api/knowledge/search`: accepts `{query, category, time_range, limit}` and returns attributed results with `title`, `extract`, `source_url`, `source`, `published`, and optional `image_url`.

## Sources
- Web: Wikipedia and GDELT news; optional SearXNG via `JON2_SEARXNG_URL`.
- News: GDELT.
- Research: Crossref and OpenAlex.
- Images: Wikimedia Commons.

No paid search API, model API, GPU, database, or credentials are required for the default configuration. Public upstreams may impose their own rate limits and occasional outages. Search is retrieval only and never claims to be the original Jon2 model.

## Deploy to Beacon.host
A free Beacon account is required for persistent Workers; it uses a one-time email code and does not require a payment card.
1. Send an OTP to the account owner's email at `POST https://beacon.host/v1/auth/send-otp`.
2. Verify the six-digit code at `POST https://beacon.host/v1/auth/verify-otp`; keep the returned API key private.
3. Create worker slug `jon2-search-api` at `POST https://beacon.host/v1/workers`.
4. Upload `worker.js` as entry point using `POST https://beacon.host/v1/workers/jon2-search-api/deploy`.
5. Verify `https://jon2-search-api.worker.beacon.host/api/health` and a real POST search.
6. Only after those checks, set the website's `JON2_API_BASE_URL` to `https://jon2-search-api.worker.beacon.host` in a separate reviewed change.

Never commit the Beacon API key. Never connect this search service to the chat composer. Do not merge or deploy this code without owner review.
