"""Multi-source web retrieval for Jon2; retrieval never trains or replaces Jon2."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import knowledge_engine

CACHE_TTL_SECONDS = 6 * 60 * 60
MAX_RESULTS = 20
MAX_EXTRACT_CHARS = 1800
USER_AGENT = "Jon2AI-Search/2.0 (+https://github.com/jonkabeel-star/jon2-ai)"
VALID_CATEGORIES = {"web", "news", "science", "images"}
TIME_RANGES = {"any", "day", "week", "month", "year"}


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
    return {word for word in _normalize(value).split() if len(word) > 1 and word not in stop}


def _fetch(url: str, accept: str = "application/json", timeout: int = 8, max_bytes: int = 1_500_000) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"upstream_http_{response.status}")
        return response.read(max_bytes)


def _json(url: str) -> dict:
    value = json.loads(_fetch(url).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Invalid upstream JSON")
    return value


def _db_path() -> Path:
    return knowledge_engine._database_path()


def _cache_init() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path), timeout=10) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS knowledge_search_cache (
            query_key TEXT PRIMARY KEY, results_json TEXT NOT NULL,
            retrieved_at INTEGER NOT NULL, expires_at INTEGER NOT NULL)""")


def _cache_key(query: str, category: str, time_range: str) -> str:
    return "|".join((_normalize(query), category, time_range))


def _cache_get(key: str, now: int) -> list[dict] | None:
    _cache_init()
    with sqlite3.connect(str(_db_path()), timeout=10) as db:
        row = db.execute("SELECT results_json FROM knowledge_search_cache WHERE query_key=? AND expires_at>?", (key, now)).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
        return data if isinstance(data, list) else None
    except (ValueError, TypeError):
        return None


def _cache_put(key: str, results: list[dict], now: int) -> None:
    _cache_init()
    with sqlite3.connect(str(_db_path()), timeout=10) as db:
        db.execute("""INSERT INTO knowledge_search_cache(query_key,results_json,retrieved_at,expires_at)
            VALUES(?,?,?,?) ON CONFLICT(query_key) DO UPDATE SET
            results_json=excluded.results_json,retrieved_at=excluded.retrieved_at,
            expires_at=excluded.expires_at""", (key, json.dumps(results, ensure_ascii=False), now, now + CACHE_TTL_SECONDS))


def _clean_query(query: str) -> str:
    language = knowledge_engine.detect_query_language(query)
    return knowledge_engine._clean_search_query(query, language)


def _searxng(query: str, category: str, time_range: str) -> list[dict]:
    base = os.getenv("JON2_SEARXNG_URL", "").strip().rstrip("/")
    if not base:
        return []
    categories = {"web": "general", "news": "news", "science": "science", "images": "images"}
    params = {
        "q": query, "format": "json", "categories": categories[category],
        "language": "all", "safesearch": "1",
    }
    if time_range != "any":
        params["time_range"] = time_range
    payload = _json(base + "/search?" + urlencode(params))
    rows = payload.get("results", [])
    results = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url", "")).strip()
        title = str(row.get("title", "")).strip()
        if not (url.startswith("https://") or url.startswith("http://")) or not title:
            continue
        image_url = str(row.get("thumbnail") or row.get("img_src") or "").strip()
        if not image_url.startswith("https://"):
            image_url = None
        results.append({
            "title": title[:300], "extract": str(row.get("content", ""))[:MAX_EXTRACT_CHARS],
            "source_url": url[:2000], "source": str(row.get("engine", "SearXNG"))[:80],
            "category": category, "published": row.get("publishedDate"),
            "image_url": image_url, "result_type": "image" if category == "images" else "webpage",
        })
    return results


def _wikipedia(query: str) -> list[dict]:
    language = knowledge_engine.detect_query_language(query)
    langs = [language] if language in {"ar", "en", "fr", "es", "de", "it", "pt", "ru", "ja", "zh"} else ["en"]
    if "en" not in langs:
        langs.append("en")
    output = []
    for lang in langs:
        params = urlencode({"action": "query", "list": "search", "srsearch": query, "srnamespace": 0, "srlimit": 5, "format": "json", "utf8": 1})
        payload = _json(f"https://{lang}.wikipedia.org/w/api.php?{params}")
        for hit in payload.get("query", {}).get("search", []):
            title = str(hit.get("title", "")).strip()
            if not title:
                continue
            summary = _json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}")
            extract = str(summary.get("extract", "")).strip()
            page = summary.get("content_urls", {}).get("desktop", {}).get("page")
            if extract and isinstance(page, str) and page.startswith("https://"):
                output.append({"title": title, "extract": extract[:MAX_EXTRACT_CHARS], "source_url": page,
                               "source": "Wikipedia", "category": "web", "published": None, "result_type": "article"})
        if output:
            break
    return output


def _gdelt_news(query: str, time_range: str) -> list[dict]:
    params_data = {"query": query, "mode": "ArtList", "format": "json", "maxrecords": 15,
                   "sort": "HybridRel"}
    days = {"day": 1, "week": 7, "month": 30, "year": 365}.get(time_range)
    if days is not None:
        params_data["startdatetime"] = time.strftime(
            "%Y%m%d%H%M%S", time.gmtime(time.time() - days * 86400)
        )
    params = urlencode(params_data)
    payload = _json("https://api.gdeltproject.org/api/v2/doc/doc?" + params)
    output = []
    for row in payload.get("articles", []):
        url = str(row.get("url", "")).strip()
        title = str(row.get("title", "")).strip()
        if url.startswith("http") and title:
            output.append({"title": title, "extract": str(row.get("seendate", "")) + " · " + str(row.get("domain", "")),
                           "source_url": url, "source": "GDELT News", "category": "news",
                           "published": row.get("seendate"), "result_type": "news"})
    return output


def _crossref(query: str) -> list[dict]:
    params = urlencode({"query.bibliographic": query, "rows": 8, "select": "title,author,published,URL,abstract"})
    payload = _json("https://api.crossref.org/works?" + params)
    output = []
    for row in payload.get("message", {}).get("items", []):
        title = (row.get("title") or [""])[0]
        url = row.get("URL")
        abstract = re.sub(r"<[^>]+>", " ", str(row.get("abstract", "")))
        if title and isinstance(url, str) and url.startswith("https://"):
            date_parts = row.get("published", {}).get("date-parts", [[]])
            published = "-".join(map(str, date_parts[0])) if date_parts and date_parts[0] else None
            output.append({"title": str(title), "extract": abstract[:MAX_EXTRACT_CHARS] or "Academic publication record.",
                           "source_url": url, "source": "Crossref", "category": "science",
                           "published": published, "result_type": "research"})
    return output


def _openalex(query: str) -> list[dict]:
    params = urlencode({"search": query, "per-page": 8, "select": "id,doi,title,publication_year,primary_location"})
    payload = _json("https://api.openalex.org/works?" + params)
    output = []
    for row in payload.get("results", []):
        title = str(row.get("title") or "").strip()
        loc = row.get("primary_location") or {}
        source_url = (loc.get("landing_page_url") if isinstance(loc, dict) else None) or row.get("doi") or row.get("id")
        if title and isinstance(source_url, str) and source_url.startswith("http"):
            output.append({"title": title, "extract": "Research work · " + str(row.get("publication_year") or "date unavailable"),
                           "source_url": source_url, "source": "OpenAlex", "category": "science",
                           "published": row.get("publication_year"), "result_type": "research"})
    return output


def _europe_pmc(query: str) -> list[dict]:
    params = urlencode({"query": query, "format": "json", "pageSize": 8, "resultType": "lite"})
    payload = _json("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params)
    output = []
    for row in payload.get("resultList", {}).get("result", []):
        title = str(row.get("title") or "").strip()
        pmid = row.get("pmid")
        doi = row.get("doi")
        url = f"https://europepmc.org/article/MED/{pmid}" if pmid else f"https://doi.org/{doi}" if doi else None
        if title and url:
            output.append({"title": title, "extract": str(row.get("journalTitle") or "Biomedical research") + " · " + str(row.get("pubYear") or ""),
                           "source_url": url, "source": "Europe PMC", "category": "science",
                           "published": row.get("firstPublicationDate"), "result_type": "research"})
    return output


def _rank(query: str, results: list[dict]) -> list[dict]:
    wanted = _terms(query)
    ranked = []
    for row in results:
        title_terms, body_terms = _terms(row.get("title", "")), _terms(row.get("extract", ""))
        if wanted:
            title_score = len(wanted & title_terms) / len(wanted)
            body_score = len(wanted & body_terms) / len(wanted)
            score = title_score * 0.72 + body_score * 0.28
        else:
            score = 0.0
        ranked.append({**row, "relevance": round(score, 4)})
    ranked.sort(key=lambda x: (x["relevance"], bool(x.get("published")), len(x.get("extract", ""))), reverse=True)
    unique, seen = [], set()
    for row in ranked:
        key = row["source_url"].split("#", 1)[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def search_knowledge(query: str, limit: int = 10, category: str = "web", time_range: str = "any") -> dict:
    query = str(query or "").strip()
    if len(query) < 3:
        return {"query": query, "results": [], "cached": False, "status": "query_too_short", "sources_used": []}
    if len(query) > 500:
        raise ValueError("Search query must be 500 characters or fewer.")
    if category not in VALID_CATEGORIES:
        raise ValueError("category must be web, news, science, or images.")
    if time_range not in TIME_RANGES:
        raise ValueError("time_range must be any, day, week, month, or year.")
    limit = max(1, min(int(limit), MAX_RESULTS))
    key = _cache_key(query, category, time_range)
    now = int(time.time())
    cached = _cache_get(key, now)
    if cached is not None:
        return {"query": query, "category": category, "time_range": time_range, "results": cached[:limit],
                "cached": True, "status": "ok" if cached else "no_results", "sources_used": sorted({x["source"] for x in cached})}
    clean = _clean_query(query)
    gathered: list[dict] = []
    errors: list[str] = []
    providers = []
    if os.getenv("JON2_SEARXNG_URL", "").strip():
        providers.append(lambda: _searxng(clean, category, time_range))
    if category == "web":
        providers.extend([lambda: _wikipedia(clean)])
    elif category == "news":
        providers.extend([lambda: _gdelt_news(clean, time_range)])
    elif category == "science":
        providers.extend([lambda: _crossref(clean), lambda: _openalex(clean), lambda: _europe_pmc(clean)])
    # SearXNG is the broad-web connector; open APIs provide independent fallback coverage.
    if providers:
        with ThreadPoolExecutor(max_workers=min(5, len(providers))) as pool:
            futures = [pool.submit(provider) for provider in providers]
            for future in futures:
                try:
                    gathered.extend(future.result(timeout=10))
                except FutureTimeout:
                    errors.append("ProviderTimeout")
                except Exception as exc:
                    errors.append(type(exc).__name__)
    ranked = _rank(clean, gathered)[:limit]
    _cache_put(key, ranked, now)
    return {"query": query, "category": category, "time_range": time_range, "results": ranked,
            "cached": False, "status": "ok" if ranked else "sources_unavailable" if errors else "no_results",
            "sources_used": sorted({x["source"] for x in ranked}),
            "source_policy": "retrieval_only_not_training"}


def answer_from_sources(result: dict) -> dict:
    rows = result.get("results") or []
    if not rows:
        return {"answer": None, "answer_type": "no_verified_retrieval", "sources": []}
    best = rows[0]
    if float(best.get("relevance", 0)) < 0.08:
        return {"answer": None, "answer_type": "weak_match",
                "sources": [{"title": x["title"], "url": x["source_url"]} for x in rows]}
    return {"answer": best.get("extract") or None, "answer_type": "retrieved_source_extract",
            "notice": "مقتطف مسترجع من المصدر، وليس إجابة مولّدة من نموذج Jon2.",
            "sources": [{"title": x["title"], "url": x["source_url"], "source": x["source"],
                         "relevance": x["relevance"]} for x in rows]}
