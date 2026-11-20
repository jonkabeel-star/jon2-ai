# Jon2 standalone search service

This folder contains a separate SearXNG metasearch service, independent from the Jon2 model API.

## Run
1. Copy `settings.example.yml` to `settings.yml`.
2. Replace the placeholder secret with a long random secret before exposing the service.
3. Run `docker compose up -d`.
4. Check `http://localhost:8080/healthz` and `/search?q=arabic&format=json`.
5. Set the Jon2 API environment variable `JON2_SEARXNG_URL=https://YOUR-SEARCH-HOST`.

Use HTTPS, protect the service from abuse, and configure rate limits/firewall rules. Public free hosts may sleep, impose resource limits, or disallow long-running containers; a free deployment is not guaranteed.
