"""Fast, source-attributed knowledge search for Jon2.

This is retrieval, not model training or a substitute language model. It searches
public MediaWiki pages, ranks several candidate summaries locally, and caches
results in SQLite. It never writes retrieved text into the training corpus.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import knowledge_engine

CACHE_TTL_SECONDS = 24 * 60 * 60
MAX_RESULTS = 5
MAX_EXTRACT_CHARS = 1400
USER_AGENT = "Jon2AI-KnowledgeSearch/1.0 (source-attributed retrieval)"


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    text = re.sub(r"[^\w\u0600-\u06ff ]+", " ", text)
    return " ".join(text.split())


def _terms(value: str) -> set[str]:
    stop = {
        "ما", "ماذا", "هو", "هي", "من", "في", "عن", "على", "الى", "إلى",
        "كيف", "لماذا", "ليه", "ايه", "يعني", "هل", "the", "what", "who",
        "how", "why", "is", "are", "for", "and", "with", "about",
    }
    return {part for part in _normalize(value).split() if len(part) > 1 and part not in stop}


def _query_for_search(query: str) -> str:
    language = knowledge_engine.detect_query_language(query)
    return knowledge_engine._clean_search_query(query, language)


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=6) as response:
        if response.status != 200:
            raise RuntimeError("Search source returned a non-success status.")
        payload = json.loads(response.read(900_000).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid search source response.")
    return payload


def _db_path() -> Path:
    return knowledge_engine._database_path()


def _initialize() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path), timeout=10) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_search_cache (
                query_key TEXT PRIMARY KEY,
                results_json TEXT NOT NULL,
                retrieved_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_search_expiry ON knowledge_search_cache(expires_at)")


def _cached(query: str, now: int) -> list[dict] | None:
    _initialize()
    key = _normalize(query)
    with sqlite3.connect(str(_db_path()), timeout=10) as db:
        row = db.execute(
            "SELECT results_json FROM knowledge_search_cache WHERE query_key=? AND expires_at>?",
            (key, now),
        ).fetchone()
    if not row:
        return None
    try:
        value = json.loads(row[0])
        return value if isinstance(value, list) else None
    except (TypeError, ValueError):
        return None


def _store(query: str, results: list[dict], now: int) -> None:
    _initialize()
    with sqlite3.connect(str(_db_path()), timeout=10) as db:
        db.execute(
            """INSERT INTO knowledge_search_cache(query_key,results_json,retrieved_at,expires_at)
               VALUES(?,?,?,?) ON CONFLICT(query_key) DO UPDATE SET
               results_json=excluded.results_json,retrieved_at=excluded.retrieved_at,
               expires_at=excluded.expires_at""",
            (_normalize(query), json.dumps(results, ensure_ascii=False), now, now + CACHE_TTL_SECONDS),
        )


def _candidate_pages(query: str, language: str) -> list[tuple[str, str]]:
    params = urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "srnamespace": 0, "srlimit": MAX_RESULTS, "srprop": "snippet",
        "format": "json", "utf8": 1,
    })
    payload = _fetch_json(f"https://{language}.wikipedia.org/w/api.php?{params}")
    hits = payload.get("query", {}).get("search", [])
    output = []
    for hit in hits:
        title = str(hit.get("title", "")).strip()
        if title:
            output.append((title, str(hit.get("snippet", ""))))
    return output


def _summary(title: str, language: str) -> dict | None:
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
    payload = _fetch_json(url)
    extract = re.sub(r"<[^>]*>", "", str(payload.get("extract", ""))).strip()
    page = payload.get("content_urls", {}).get("desktop", {}).get("page")
    if not extract or not isinstance(page, str) or not page.startswith(f"https://{language}.wikipedia.org/"):
        return None
    return {
        "title": title[:240],
        "extract": extract[:MAX_EXTRACT_CHARS],
        "source_url": page,
        "language": language,
    }


def _rank(query: str, records: list[dict]) -> list[dict]:
    wanted = _terms(query)
    ranked = []
    for record in records:
        title_terms = _terms(record.get("title", ""))
        body_terms = _terms(record.get("extract", ""))
        if not wanted:
            score = 0.0
        else:
            title_match = len(wanted & title_terms) / len(wanted)
            body_match = len(wanted & body_terms) / len(wanted)
            score = round(min(1.0, title_match * 0.75 + body_match * 0.25), 4)
        ranked.append({**record, "relevance": score})
    return sorted(ranked, key=lambda item: (item["relevance"], len(item["extract"])), reverse=True)


def search_knowledge(query: str, limit: int = MAX_RESULTS) -> dict:
    """Search in the query language, use English fallback, rank, and cache sources."""
    cleaned = str(query or "").strip()
    if len(cleaned) < 3:
        return {"query": cleaned, "results": [], "cached": False, "status": "query_too_short"}
    if len(cleaned) > 500:
        raise ValueError("Search query must be 500 characters or fewer.")
    limit = max(1, min(int(limit), MAX_RESULTS))
    language = knowledge_engine.detect_query_language(cleaned)
    search_query = _query_for_search(cleaned)
    now = int(time.time())
    cached = _cached(cleaned, now)
    if cached is not None:
        return {
            "query": cleaned, "results": cached[:limit], "cached": True,
            "status": "ok" if cached else "no_results",
            "source_policy": "retrieval_only_not_training",
        }

    candidates = [language]
    fallback = "en" if language != "en" else "ar"
    if fallback not in candidates:
        candidates.append(fallback)
    records = []
    errors = []
    for candidate_language in candidates:
        try:
            pages = _candidate_pages(search_query, candidate_language)
            for title, _snippet in pages:
                try:
                    item = _summary(title, candidate_language)
                    if item and all(old["source_url"] != item["source_url"] for old in records):
                        records.append(item)
                except Exception as error:
                    errors.append(type(error).__name__)
            if len(records) >= limit:
                break
        except Exception as error:
            errors.append(type(error).__name__)
    ranked = _rank(cleaned, records)[:limit]
    _store(cleaned, ranked, now)
    return {
        "query": cleaned,
        "results": ranked,
        "cached": False,
        "status": "ok" if ranked else "source_unavailable" if errors else "no_results",
        "source_policy": "retrieval_only_not_training",
    }


def answer_from_sources(search_result: dict) -> dict:
    """Expose a cited source extract; do not pretend it was generated by Jon2."""
    results = search_result.get("results") or []
    if not results:
        return {
            "answer": None,
            "answer_type": "no_verified_retrieval",
            "sources": [],
        }
    best = results[0]
    # Avoid presenting weak lexical matches as an answer.
    if float(best.get("relevance", 0)) < 0.12:
        return {
            "answer": None,
            "answer_type": "weak_match",
            "sources": [
                {"title": item["title"], "url": item["source_url"]}
                for item in results
            ],
        }
    return {
        "answer": best["extract"],
        "answer_type": "retrieved_source_extract",
        "notice": "هذا مقتطف من مصدر مسترجع، وليس إجابة مولّدة من نموذج Jon2.",
        "sources": [
            {"title": item["title"], "url": item["source_url"], "relevance": item["relevance"]}
            for item in results
        ],
    }
