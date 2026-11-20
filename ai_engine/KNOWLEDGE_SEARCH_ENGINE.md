# Jon2 multi-source search v2

This branch upgrades retrieval from Wikipedia-only lookup to multi-source search. It does not index the whole internet and does not use an external generative AI model.

## Sources
- **SearXNG (optional self-hosted metasearch):** broad web, news, images, and configured science engines. Set `JON2_SEARXNG_URL` to its HTTPS base URL; JSON output must be enabled.
- **Wikipedia / MediaWiki:** general reference fallback.
- **GDELT DOC API:** news discovery with day/week/month/year filtering.
- **Crossref, OpenAlex, Europe PMC:** scholarly and biomedical research metadata.

The API merges, deduplicates, and ranks results locally. Lexical relevance is a heuristic, not semantic understanding or a truth score.

## API
`POST /api/knowledge/search`

```json
{"query":"الذكاء الاصطناعي","category":"web","time_range":"week","limit":10}
```
Categories: `web`, `news`, `science`, `images`. Time ranges: `any`, `day`, `week`, `month`, `year`. Limit: 1–20.

Without a configured SearXNG URL, the general-web category only falls back to Wikipedia; it is not broad web search. News and science use their own public APIs.

## Standalone search server
`search_service/` contains a separate SearXNG Docker Compose configuration. The service is not deployed by this PR. Configure Jon2 with `JON2_SEARXNG_URL` after hosting it.

## Reliability and privacy
- Six-hour SQLite cache, scoped by query/category/time range.
- Upstream failures are isolated; successful providers can still return results.
- Search queries are sent to public upstream providers; do not submit secrets or private data.
- Retrieved pages are not copied into training data and never change model weights.
- Coverage depends on configured engines and upstream availability.
- Image search returns provider metadata/URLs; it does not proxy image bytes.

## Limits
No full-web crawler, proprietary Google index, guaranteed completeness, or Google-equivalent ranking. No model training, model replacement, or chat release-gate bypass. No service deployment, paid resource creation, or DNS changes.
