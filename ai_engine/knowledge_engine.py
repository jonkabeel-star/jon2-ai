"""Small, source-attributed Arabic knowledge cache for Jon2.

This is retrieval, not model training. It uses the public MediaWiki API,
stores short extracts locally in SQLite, and keeps source URLs and timestamps.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_DB = Path.home() / ".jon2-ai" / "knowledge.sqlite3"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_EXTRACT_CHARS = 1800
USER_AGENT = "Jon2AI/1.0 (public knowledge retrieval; contact: project repository)"


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = re.sub(r"[^\w\u0600-\u06ff ]+", " ", value)
    return " ".join(value.split())


def _database_path() -> Path:
    configured = os.getenv("JON2_KNOWLEDGE_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_DB


def _connect():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                query_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                extract TEXT NOT NULL,
                source_url TEXT NOT NULL,
                retrieved_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_expiry ON knowledge(expires_at)")


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError("Knowledge source returned a non-success status.")
        payload = json.loads(response.read(1_000_000).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid knowledge source response.")
    return payload


def _search_wikipedia(query: str) -> dict | None:
    # Remove common Arabic question wrappers so the encyclopedia receives a topic.
    search_query = str(query or "").strip()
    for prefix in ("ما هو", "ماهي", "ما هي", "من هو", "من هي", "ما معنى", "معنى", "اشرح", "أشرح", "معلومات عن", "ما المقصود"):
        if _normalize(search_query).startswith(_normalize(prefix) + " "):
            search_query = search_query[len(prefix):].strip()
            break
    search_query = re.sub(r"[؟?!.،,]+$", "", search_query).strip() or str(query).strip()
    params = urlencode({
        "action": "query", "list": "search", "srsearch": search_query,
        "srnamespace": 0, "srlimit": 1, "format": "json",
        "utf8": 1,
    })
    search = _fetch_json("https://ar.wikipedia.org/w/api.php?" + params)
    hits = search.get("query", {}).get("search", [])
    if not hits:
        # English fallback helps with technical names; answer remains attributed.
        params = urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srnamespace": 0, "srlimit": 1, "format": "json",
            "utf8": 1,
        })
        search = _fetch_json("https://en.wikipedia.org/w/api.php?" + params)
        hits = search.get("query", {}).get("search", [])
        language = "en"
    else:
        language = "ar"
    if not hits:
        return None

    title = str(hits[0].get("title", "")).strip()
    if not title:
        return None
    summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
    summary = _fetch_json(summary_url)
    extract = re.sub(r"<[^>]*>", "", str(summary.get("extract", ""))).strip()
    page = summary.get("content_urls", {}).get("desktop", {}).get("page")
    if not extract or not isinstance(page, str) or not page.startswith("https://"):
        return None
    return {
        "title": title[:300],
        "extract": extract[:MAX_EXTRACT_CHARS],
        "source_url": page,
    }


def get_cached(query: str, now: int | None = None) -> dict | None:
    key = _normalize(query)
    if len(key) < 2:
        return None
    initialize()
    current = int(time.time() if now is None else now)
    with _connect() as db:
        row = db.execute(
            "SELECT title,extract,source_url,retrieved_at,expires_at "
            "FROM knowledge WHERE query_key=? AND expires_at>?",
            (key, current),
        ).fetchone()
    return dict(row) if row else None


def store(query: str, item: dict, now: int | None = None) -> None:
    key = _normalize(query)
    title = str(item.get("title", "")).strip()
    extract = str(item.get("extract", "")).strip()[:MAX_EXTRACT_CHARS]
    source_url = str(item.get("source_url", "")).strip()
    if not key or not title or not extract or not source_url.startswith("https://"):
        raise ValueError("Knowledge record is missing a valid title, extract, or HTTPS source.")
    current = int(time.time() if now is None else now)
    initialize()
    with _connect() as db:
        db.execute(
            """INSERT INTO knowledge(query_key,title,extract,source_url,retrieved_at,expires_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(query_key) DO UPDATE SET
               title=excluded.title, extract=excluded.extract, source_url=excluded.source_url,
               retrieved_at=excluded.retrieved_at, expires_at=excluded.expires_at""",
            (key, title, extract, source_url, current, current + CACHE_TTL_SECONDS),
        )


def retrieve_knowledge(query: str) -> dict | None:
    """Return a fresh cached fact, otherwise fetch and cache a Wikipedia summary."""
    cleaned = str(query or "").strip()
    if len(cleaned) < 3:
        return None
    cached = get_cached(cleaned)
    if cached:
        cached["cached"] = True
        return cached
    try:
        item = _search_wikipedia(cleaned)
        if not item:
            return None
        store(cleaned, item)
        item.update({"retrieved_at": int(time.time()), "cached": False})
        return item
    except Exception:
        # Network errors must not crash chat or be mistaken for verified knowledge.
        return None


_GREETING_RE = re.compile(
    r"^(?:السلام عليكم|السلام عليكو|سلام عليكم|مرحبا|مرحباً|اهلا|أهلا|اهلين|أهلين|هلا|هاي|"
    r"صباح الخير|مساء الخير|ازيك|إزيك|عامل ايه|عامل إيه|كيف حالك|hello|hi|hey)"
    r"[\s!！،,.؟?]*$",
    re.IGNORECASE,
)


def local_greeting(message: str) -> str | None:
    value = str(message or "").strip()
    if not value or len(value) > 60:
        return None
    if _GREETING_RE.fullmatch(value):
        return "أهلًا وسهلًا! أنا Jon2 AI. كيف أقدر أساعدك؟"
    return None


_SEARCH_STARTERS = (
    "ما هو", "ماهي", "ما هي", "من هو", "من هي", "متى", "اين", "أين",
    "فين", "ازاي", "إزاي", "كيف", "لماذا", "ليه", "كم", "ما معنى",
    "معنى", "اشرح", "أشرح", "عرف", "عرّف", "معلومات عن", "ابحث عن",
    "ما المقصود", "هل ",
)


def looks_like_fact_question(message: str) -> bool:
    value = str(message or "").strip()
    if not value:
        return False
    normalized = _normalize(value)
    # Personal/session questions belong to conversation memory, not public web search.
    if normalized.startswith(("ما اسمي", "اسمي", "من انا", "مين انا", "ماذا قلت", "ايه اللي قلته")):
        return False
    return ("؟" in value or "?" in value or
            any(normalized.startswith(_normalize(prefix)) for prefix in _SEARCH_STARTERS))


def format_knowledge_answer(item: dict) -> str:
    title = str(item.get("title", "مصدر معرفي")).strip()
    extract = str(item.get("extract", "")).strip()
    source = str(item.get("source_url", "")).strip()
    if not extract or not source.startswith("https://"):
        raise ValueError("Knowledge result is incomplete.")
    return f"{title}:\n{extract}\n\nالمصدر: ويكيبيديا — {source}\nملاحظة الترخيص: يُرجى مراجعة صفحة المصدر لتفاصيل الإسناد وترخيص المحتوى (CC BY-SA). "
