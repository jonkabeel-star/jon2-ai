# Jon2 AI — Build Plan

## Product goal
A public Arabic-first AI platform owned and developed as the Jon2 AI project. Visitors will eventually create accounts, sign in, use free tools under fair-use limits, and see clearly labeled ads on eligible public pages after the site is approved by the ad provider.

## Ownership and model transparency
- Jon2 application code, API, account system, interface, data model, and training pipeline are developed for this repository.
- The first original language-model implementation is in `ai_engine/jon2_core.py`.
- It uses a small decoder-only Transformer initialized with random weights. It is not a pretrained model and does not download another company's model weights.
- A random model is not intelligent yet. It must be trained on a large, high-quality corpus that Jon2 has permission to use, with suitable compute. A small training run is only a technical prototype and will not provide ChatGPT-level quality.
- No user-facing claim should say the model is trained, production-ready, or fully independent until it has actually been trained, evaluated, and deployed.

## Numbered implementation phases
1. **Original model foundation:** implement and document Jon2's own model architecture and training pipeline. (Started in this commit.)
2. **Data and training:** curate permitted Arabic and multilingual datasets, document licenses and sources, train checkpoints, and evaluate quality and safety.
3. **Backend platform:** add robust API, rate limits, logging, model lifecycle, and deployment configuration.
4. **Accounts and privacy:** add secure registration, sign-in, password hashing, sessions, email verification, and per-user data isolation.
5. **Public website:** connect the existing frontend to the API, add product pages, privacy policy, terms, and account screens.
6. **Free-use controls:** apply transparent fair-use limits and abuse protection without surprise charges.
7. **Ads readiness:** add non-intrusive ad placements only on suitable public content pages; apply to the ad program only after policy and eligibility checks.
8. **Launch and monitoring:** load testing, security review, backups, incident handling, and gradual public release.

## Important operating constraints
- GitHub Pages can host static frontend files; it does not run the Python model or securely store user accounts.
- A public AI service requires a backend host with enough RAM/CPU/GPU. "Free for visitors" does not mean infrastructure has zero cost.
- Do not put secrets, passwords, API keys, or private training data in the public repository.
- Do not promise AdSense approval or revenue; both depend on review, traffic, policy compliance, and advertiser demand.

## Training data format
Place UTF-8 plain-text files (`.txt`) in `ai_engine/training_data/`. Use only text that Jon2 owns or is licensed to use. Keep a separate record of each dataset's source, license, date obtained, and permitted use. Do not commit private or personal data.

## Public platform, video publishing, and monetization requirements

The detailed implementation contract is in `PUBLIC_PLATFORM_BLUEPRINT.md`. These requirements are part of the project plan:

- Public accounts must use server-side password hashing, verified email, secure sessions, CSRF protection, account recovery/deletion, and per-user authorization. Never implement a fake browser-only login.
- Use a persistent database and private object storage; GitHub Pages is frontend hosting only.
- Every AI tool must be honestly marked Available, Beta, or Coming soon based on a real working backend.
- The Video Studio should generate a draft workflow first: original script, scene plan, media, voice, captions, and preview.
- YouTube connection must use Google's official OAuth flow with the minimum upload scope. Keep refresh tokens encrypted server-side.
- Each upload requires explicit owner approval tied to the exact final video version. Start with private/unlisted test uploads; do not enable unattended public publishing by default.
- AdSense is a future integration. Reserve clear ad placements, but add official ad code only after eligibility and approval. Never incentivize ad clicks or promise one ad per tool action.
- Copyright-sensitive datasets and assets remain excluded unless the project has documented permission for the exact intended use.

## Current gateway safety status

`server/server.js` now uses a production-site CORS allowlist by default, a request-size limit, a message-length limit, and a temporary per-process rate limit. This is a security improvement, not a complete production security system. Persistent rate limiting, accounts, database storage, monitoring, and deployment are still required.
