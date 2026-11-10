# Jon2 Independent Core — first isolated runtime

## Purpose

This is a separate FastAPI entry point for the original Jon2 model. Its answer
path uses only:

- the project's own checkpoint loaded by `ai_engine/chat_engine.py`;
- the project's SQLite conversation-memory module, `ai_engine/chat_memory.py`.

It does not call Cloudflare Workers AI, a hosted LLM, web search, Wikipedia, or
a third-party model fallback. A missing or failing Jon2 checkpoint produces an
error; the runtime must never silently switch to another provider.

## Important current limitation

The existing 269,952-parameter checkpoint completed a real training run, but
its held-out Arabic answers were incoherent. Therefore:

- `JON2_INDEPENDENT_CHAT_RELEASE_APPROVED` must remain `false`;
- `POST /api/chat` must remain unavailable to visitors;
- a successful API health response is not a model-quality pass;
- this runtime is not yet connected to the public website and is not deployed.

## Local smoke-test setup

From the repository root, install the dependencies already listed in
`requirements.txt`, then start this isolated API:

```bash
uvicorn independent_api:app --app-dir ai_engine --host 127.0.0.1 --port 8001
```

Check:

- `GET http://127.0.0.1:8001/`
- `GET http://127.0.0.1:8001/api/health`
- `GET http://127.0.0.1:8001/api/health/ready`

Readiness is expected to return HTTP 503 until a reviewed checkpoint is loaded
and the explicit human release gate is approved. Do not enable the gate for the
current incoherent checkpoint.

## Persistent memory

SQLite uses the existing `JON2_MEMORY_DB_PATH` setting and defaults to
`~/.jon2-ai/memory.sqlite3`. On a hosted server, this file must live on a
persistent disk or durable mounted volume. An ephemeral filesystem can lose
the conversation history on restart or redeploy.

A session UUID is a locator, not account authentication. Before this API is
exposed to multiple public users, add real user authentication and bind every
session to its authenticated owner. Do not treat an unguessable session ID as
a complete privacy/security boundary.

## Release gates still required

1. Improve the original model using a substantially larger, rights-cleared,
   high-quality Arabic corpus. Never duplicate text to inflate the corpus.
2. Keep held-out prompts separate from training data.
3. Run the full held-out evaluation and obtain documented human semantic review.
4. Add authentication, per-user session ownership, rate limits, request limits,
   and operational monitoring before public exposure.
5. Deploy to a host with enough CPU/GPU, RAM, and persistent storage; measure
   real inference latency and concurrent-user capacity.
6. Only then consider enabling
   `JON2_INDEPENDENT_CHAT_RELEASE_APPROVED=true` for the exact approved
   checkpoint.

## Ownership and uptime

The source code, model architecture, trained weights, and memory schema can be
owned and moved by the project. That does not make public hosting free or
permanent: an online shared service still needs a running computer/server,
power, network access, storage, and maintenance. No hosting provider or
lifetime-free uptime is promised by this code.
