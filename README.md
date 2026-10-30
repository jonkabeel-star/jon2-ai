# Jon2 AI

Jon2 AI is an independent Arabic-first AI platform project.

## Project status

This repository contains the website interface, an early model prototype, and the first API gateway. It is **not yet a public production AI service**: secure user accounts, persistent storage, a deployed model runtime, video rendering, YouTube OAuth/upload, and AdSense are not live yet.

## Start here

- [Public platform blueprint](PUBLIC_PLATFORM_BLUEPRINT.md) — architecture, secure accounts, AI tools, video workflow, YouTube approvals, and AdSense readiness.
- [Build plan](JON2_AI_BUILD_PLAN.md) — staged implementation plan.
- [Authentication setup](server/AUTH_SETUP.md) — account API endpoints, required secrets, database migration, and deployment gates.\n- [Original data policy](ai_engine/ORIGINAL_DATA_POLICY.md) — requirements for training text and asset permissions.
- [Dataset register](ai_engine/DATASET_REGISTER.md) — current dataset approval decisions.

## Hosting boundaries

GitHub Pages can host the static website only. It cannot run the Python model, store passwords securely, or act as the production database. The API and model need a separate HTTPS backend, persistent database, private file storage, and managed secrets.

## Safety and rights

The project avoids web-scraped training corpora and unverified media rights. Use only original project content, user-owned material, commissioned material, or sources with documented permissions for the intended use. Do not commit secrets, user passwords, private tokens, or private training corpora.

## Current backend

The Node.js API gateway is in `server/server.js`. Initial account routes and Argon2id/session handling are in `server/auth.js`; dependencies are listed in `server/package.json`, and required environment settings are documented in `server/.env.example`. The PostgreSQL schema and migration command are in `server/db/schema.sql` and `server/migrate.js`. These are implementation files only: no live database, SMTP provider, backend deployment, same-site custom domain, or end-to-end security test has been configured. The static website is not yet connected to the account API. Do not expose it as a public multi-user service until the launch gates in the blueprint are complete.
