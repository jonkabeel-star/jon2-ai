# Jon2 AI

Jon2 AI is an independent Arabic-first AI platform project.

## Project status

This repository contains the website interface, an early original-model prototype, and the first API gateway. It is **not yet a public production AI service**. A deployed Python model runtime, approved training corpus, quality-approved checkpoint, persistent database, secure public accounts, video rendering, YouTube OAuth/upload, and AdSense are not live.

## Start here

- [Public platform blueprint](PUBLIC_PLATFORM_BLUEPRINT.md) — architecture, secure accounts, AI tools, video workflow, YouTube approvals, and AdSense readiness.
- [Build plan](JON2_AI_BUILD_PLAN.md) — staged implementation plan.
- [Authentication setup](server/AUTH_SETUP.md) — account API endpoints, required secrets, database migration, and deployment gates.
- [Original data policy](ai_engine/ORIGINAL_DATA_POLICY.md) — requirements for training text and asset permissions.
- [Dataset register](ai_engine/DATASET_REGISTER.md) — current dataset approval decisions.
- [Original model API guide](ai_engine/README.md) — local API, training safeguards, and evaluation instructions.

## Website chat connection

The static chat interface can call the original FastAPI model API when a backend is deployed. Set `window.JON2_API_BASE_URL` to the backend HTTPS origin before the main inline script loads. The page checks `/api/health` and sends chat messages to `/api/chat`. If no URL is configured, it reports that the backend is not deployed. The API must allow the GitHub Pages origin through CORS.

The chat must remain unavailable until a real Jon2 checkpoint passes the project's Arabic-output checks and human review. A running API alone does not mean the model is ready.

## Hosting boundaries

GitHub Pages hosts the static website only. It cannot run the Python model, store passwords securely, or act as the production database. The model API needs a separate HTTPS backend and private checkpoint storage. Account services additionally need a persistent database, managed secrets, and a verified email provider.

## Safety and rights

Use only original project content, user-owned material, commissioned material, or sources with documented permissions for the intended use. Do not commit secrets, user passwords, private tokens, private training corpora, or private model checkpoints.

The source-approval workflow intentionally blocks training unless every exact source file has an explicit approval record bound to its SHA-256 hash and character count. A missing approval is a safety stop, not a workflow defect.

## Current backend

The Node.js API gateway is in `server/server.js`. Initial account routes, email verification, password reset, and Argon2id/session handling are in `server/auth.js`; dependencies are listed in `server/package.json`, and required environment settings are documented in `server/.env.example`. The PostgreSQL schema and migration command are in `server/db/schema.sql` and `server/migrate.js`.

These are implementation files only. No live database, SMTP provider, backend deployment, same-site custom domain, or end-to-end security test has been configured. The static website is not yet connected to the account API. Do not expose it as a public multi-user service until the launch gates in the blueprint are complete.
