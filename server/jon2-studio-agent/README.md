# Jon2 Studio Agent API

A small, self-hosted API for the Studio coding assistant. It provides authenticated chat, bounded project-file context, and persistent SQLite conversation history. It does **not** bundle a language model and does not execute generated code.

## Requirements

- Python 3.11+
- A separately hosted local model server that exposes an OpenAI-compatible \`/v1/chat/completions\` endpoint (for example, a self-hosted Ollama or llama.cpp server)
- A persistent disk for \`memory.sqlite3\`

## Configure

Set these environment variables on the Linux host:

- \`JON2_AGENT_TOKEN\`: long random secret; required.
- \`JON2_MODEL_BASE_URL\`: model server base URL ending before \`/chat/completions\`, e.g. \`http://127.0.0.1:11434/v1\`.
- \`JON2_MODEL_NAME\`: exact model identifier accepted by that server.
- \`JON2_AGENT_ORIGINS\`: comma-separated exact Studio origins. Keep the default for local development; replace it with the deployed Studio origin only after access control is verified.
- \`JON2_AGENT_DB\`: optional persistent SQLite path.
- \`JON2_MODEL_TIMEOUT\`: optional request timeout in seconds.

Install and run:

\`\`\`bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8789
\`\`\`

Check \`GET /health\`. A healthy process is not proof that a model is ready: both \`model_configured\` and \`authentication_configured\` must be true, and a real authenticated chat request must succeed.

## API

- \`GET /health\`: non-secret readiness indicators.
- \`POST /v1/agent/chat\`: authenticated chat with optional session id and project files.
- \`DELETE /v1/agent/memory/{session_id}\`: delete one conversation's server-side memory.

Use \`Authorization: Bearer <JON2_AGENT_TOKEN>\`.

## Safety and privacy

- Project context is sent to the configured model server. Use a model server you control and do not send secrets.
- Files named like \`.env\`, \`secret\`, \`credential\`, \`token\`, or \`private_key\` are excluded. This is a guardrail, not a guarantee that secrets cannot appear in ordinary source files.
- Request size is bounded. Only the latest 20 messages are sent to the model.
- Conversation text is stored in SQLite until explicitly deleted or the database is removed.
- No shell, filesystem-write, GitHub, deployment, or code-execution tools are exposed by this API.
- Put the API behind HTTPS and a firewall. Do not expose the model server publicly. Use a unique token and rotate it if disclosed.
- Do not deploy this API on Cloudflare Pages: Pages serves static assets and cannot run this Python service. A separate Linux host is required.

## Cost

The code is free/open source, but a host, storage, bandwidth, and compute may have provider limits or costs. Do not assume a free host or free GPU is permanent. This API does not automatically upgrade any plan.
