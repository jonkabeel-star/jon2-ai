# Jon2 standalone search service

This folder contains a separate SearXNG metasearch service, independent from the Jon2 model API.

## Run with Docker Compose
1. Copy `settings.example.yml` to `settings.yml`.
2. Copy `.env.example` to `.env` and replace the placeholder with a long random secret. Never commit the secret or `.env`.
3. Run `docker compose up -d`.
4. Check `http://localhost:8080/healthz` and `/search?q=arabic&format=json`.
5. Set the Jon2 API environment variable `JON2_SEARXNG_URL=https://YOUR-SEARCH-HOST`.

## Optional Render free-tier blueprint
The repository root contains `render.search.yaml`. In Render, create a Blueprint and select that file. It requests a free web service and asks Render to generate `SEARXNG_SECRET`. Free services can sleep after inactivity, have limited memory/CPU, and may be unsuitable for steady public search. Availability and limits are controlled by Render and can change; no service is created by this repository change.

Important: the minimal configuration disables SearXNG's Valkey-backed limiter to avoid requiring a second service. Do not expose it as an unrestricted public endpoint without adding rate limiting or an access-control reverse proxy. Use HTTPS and a strong generated secret. Render's free web service has 512 MB RAM, spins down after 15 minutes without inbound traffic, wakes with a cold start, and has ephemeral storage; this is suitable only for a low-traffic experiment, not dependable always-on search. No service is created by these files.
