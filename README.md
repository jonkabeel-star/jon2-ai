# Jon2 AI

Jon2 AI is an independent Arabic-first AI platform project.

## Project status

This repository contains the website interface, an early original-model prototype, and the first API gateway. A first genuine CPU-trained Jon2 checkpoint is now stored privately, but its Arabic replies are not coherent enough for user-facing chat. It is **not yet a public production AI service**. A deployed Python model runtime, approved training corpus, quality-approved checkpoint, persistent database, secure public accounts, video rendering, YouTube OAuth/upload, and AdSense are not live.

## Start here

- [Public platform blueprint](PUBLIC_PLATFORM_BLUEPRINT.md) — architecture, secure accounts, AI tools, video workflow, YouTube approvals, and AdSense readiness.
- [Build plan](JON2_AI_BUILD_PLAN.md) — staged implementation plan.
- [Authentication setup](server/AUTH_SETUP.md) — account API endpoints, required secrets, database migration, and deployment gates.
- [Original data policy](ai_engine/ORIGINAL_DATA_POLICY.md) — requirements for training text and asset permissions.
- [Dataset register](ai_engine/DATASET_REGISTER.md) — current dataset approval decisions.
- [Original model API guide](ai_engine/README.md) — local API, training safeguards, and evaluation instructions.
- [Backend deployment notes](ai_engine/DEPLOYMENT.md) — CPU-only container build, health checks, and safe release configuration.

## Website chat connection

The static chat interface can call the original FastAPI model API when a backend is deployed. Set `window.JON2_API_BASE_URL` to the backend HTTPS origin before the main inline script loads. The page checks `/api/health` and sends chat messages to `/api/chat`. If no URL is configured, it reports that the backend is not deployed. The API must allow the GitHub Pages origin through CORS.

The chat must remain unavailable until a real Jon2 checkpoint passes the project's Arabic-output checks and human review. A running API alone does not mean the model is ready. The browser client checks `/api/health`, displays the difference between API liveness and model readiness, and posts each message with a browser-generated UUID `session_id` to `/api/chat`; the FastAPI service stores the exchange in its private SQLite memory. The client accepts only an HTTPS API origin (HTTP is allowed for localhost development), and the backend CORS allowlist includes the GitHub Pages origin.

For GitHub Pages, edit the single setting in the root `jon2-config.js` file to `window.JON2_API_BASE_URL = "https://YOUR-DEPLOYED-API-HOST";` after the API is deployed. The file is loaded before the chat client, accepts only an HTTPS origin (or localhost HTTP for development), and must contain no credentials or private tokens. Until an owner deploys the API and configures that origin, the GitHub Pages site correctly reports that no backend is connected.

## Source-backed knowledge retrieval

The chat API has a lightweight Arabic greeting path and a source-attributed factual lookup path. Factual lookups use the public Arabic Wikipedia API (with an English-language fallback), save the short extract, title, source URL, retrieval time, and expiry in a local SQLite cache, and reuse fresh entries for seven days. This is retrieval/cache behavior; it does not update the model weights or add retrieved pages to the approved training corpus.

The cache database defaults to `~/.jon2-ai/knowledge.sqlite3`. Set `JON2_KNOWLEDGE_DB_PATH` to choose another writable path. On hosts with an ephemeral filesystem (including typical free web-service instances), cached knowledge may be lost when the service is restarted or redeployed. Durable cross-restart storage requires a persistent volume or managed database.

The API health response reports the retrieval/cache configuration. Offline unit tests run in the `Jon2 Knowledge Retrieval Tests` GitHub Actions workflow. General model chat remains gated by the existing human release approval.

## Hosting boundaries

GitHub Pages hosts the static website only. It cannot run the Python model, store passwords securely, or act as the production database. The model API needs a separate HTTPS backend and private checkpoint storage. Account services additionally need a persistent database, managed secrets, and a verified email provider.

## Safety and rights

Use only original project content, user-owned material, commissioned material, or sources with documented permissions for the intended use. Do not commit secrets, user passwords, private tokens, private training corpora, or private model checkpoints.

The source-approval workflow intentionally blocks training unless every exact source file has an explicit approval record bound to its SHA-256 hash and character count. A missing approval is a safety stop, not a workflow defect.

## Current backend

The Node.js API gateway is in `server/server.js`. Initial account routes, email verification, password reset, and Argon2id/session handling are in `server/auth.js`; dependencies are listed in `server/package.json`, and required environment settings are documented in `server/.env.example`. The PostgreSQL schema and migration command are in `server/db/schema.sql` and `server/migrate.js`.

These are implementation files only. No live database, SMTP provider, backend deployment, same-site custom domain, or end-to-end security test has been configured. The static website is not yet connected to the account API. Do not expose it as a public multi-user service until the launch gates in the blueprint are complete.
