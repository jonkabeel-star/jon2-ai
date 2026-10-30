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
