"""Source-attributed multilingual factual retrieval for Jon2.

Uses public MediaWiki search/summary endpoints and a bounded SQLite cache.
Retrieval is not model training and never changes model weights.
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
USER_AGENT = "Jon2AI/1.1 (public knowledge retrieval; contact: project repository)"

# Script detection is deterministic. Latin-script languages use small function-word
# signatures; ambiguous Latin text safely defaults to English.
LATIN_SIGNATURES = {
    "en": {"the", "what", "who", "when", "where", "why", "how", "is", "are", "of", "for"},
    "fr": {"le", "la", "les", "des", "est", "qui", "quoi", "comment", "pour", "avec", "qu'est", "ce", "une"},
    "es": {"el", "la", "los", "las", "que", "como", "cómo", "quien", "qué", "para", "es", "una"},
    "de": {"der", "die", "das", "ist", "wer", "was", "wie", "warum", "und", "mit"},
    "it": {"il", "lo", "gli", "che", "come", "chi", "cosa", "per", "con", "una", "cos'è", "la"},
    "pt": {"o", "os", "as", "que", "como", "quem", "uma", "para", "com", "não"},
    "nl": {"de", "het", "een", "wie", "wat", "waar", "hoe", "waarom", "met", "voor", "kunstmatige", "intelligentie"},
}
SCRIPT_LANGUAGES = (
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("hi", re.compile(r"[\u0900-\u097f]")),
    ("th", re.compile(r"[\u0e00-\u0e7f]")),
    ("el", re.compile(r"[\u0370-\u03ff]")),
    ("he", re.compile(r"[\u0590-\u05ff]")),
)
QUESTION_STARTERS = {
    "ar": ("ما هو", "ماهي", "ما هي", "من هو", "من هي", "متى", "اين", "أين", "فين", "ازاي", "إزاي", "كيف", "لماذا", "ليه", "كم", "ما معنى", "معنى", "اشرح", "معلومات عن", "ابحث عن", "ما المقصود", "هل "),
    "en": ("what is", "who is", "when", "where", "why", "how", "define", "explain", "search for", "tell me about"),
    "fr": ("qu'est-ce", "qui est", "quand", "où", "pourquoi", "comment", "définis", "explique"),
    "es": ("qué es", "quién es", "cuándo", "dónde", "por qué", "cómo", "explica", "define"),
    "de": ("was ist", "wer ist", "wann", "wo", "warum", "wie", "erkläre"),
    "it": ("che cos'è", "cos'è", "chi è", "quando", "dove", "perché", "come", "spiega"),
    "pt": ("o que é", "quem é", "quando", "onde", "por que", "como", "explique"),
    "nl": ("wat is", "wie is", "wanneer", "waar", "waarom", "hoe", "leg uit"),
}


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or "")).lower()
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = re.sub(r"[^\w\u0600-\u06ff ]+", " ", value)
    return " ".join(value.split())


def detect_query_language(text: str) -> str:
    """Best-effort language routing; this is not a full language-identification model."""
    value = str(text or "")
    for language, pattern in SCRIPT_LANGUAGES:
        if pattern.search(value):
            return language
    words = set(re.findall(r"[a-zA-ZÀ-ÿ']+", value.lower()))
    scores = {lang: len(words & signature) for lang, signature in LATIN_SIGNATURES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "en"


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
                query_key TEXT PRIMARY KEY, title TEXT NOT NULL, extract TEXT NOT NULL,
                source_url TEXT NOT NULL, retrieved_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
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


def _clean_search_query(query: str, language: str) -> str:
    value = str(query or "").strip()
    for prefix in QUESTION_STARTERS.get(language, ()):
        if value.lower().startswith(prefix.lower() + " ") or value.lower() == prefix.lower():
            value = value[len(prefix):].strip()
            break
    return re.sub(r"[؟?!.،,;；。]+$", "", value).strip() or str(query).strip()


def _search_wikipedia(query: str) -> dict | None:
    language = detect_query_language(query)
    search_query = _clean_search_query(query, language)
    # Search in the user's language first; use English as a technical-topic fallback.
    candidates = [language] if language != "en" else ["en"]
    fallback = "en" if language != "en" else "ar"
    candidates.append(fallback)
    for candidate in candidates:
        params = urlencode({
            "action": "query", "list": "search", "srsearch": search_query,
            "srnamespace": 0, "srlimit": 1, "format": "json", "utf8": 1,
        })
        search = _fetch_json(f"https://{candidate}.wikipedia.org/w/api.php?" + params)
        hits = search.get("query", {}).get("search", [])
        if not hits:
            continue
        title = str(hits[0].get("title", "")).strip()
        if not title:
            continue
        summary_url = f"https://{candidate}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
        summary = _fetch_json(summary_url)
        extract = re.sub(r"<[^>]*>", "", str(summary.get("extract", ""))).strip()
        page = summary.get("content_urls", {}).get("desktop", {}).get("page")
        if extract and isinstance(page, str) and page.startswith("https://"):
            return {
                "title": title[:300], "extract": extract[:MAX_EXTRACT_CHARS],
                "source_url": page, "language": candidate,
            }
    return None


def get_cached(query: str, now: int | None = None) -> dict | None:
    key = _normalize(query)
    if len(key) < 2:
        return None
    initialize()
    current = int(time.time() if now is None else now)
    with _connect() as db:
        row = db.execute(
            "SELECT title,extract,source_url,retrieved_at,expires_at FROM knowledge WHERE query_key=? AND expires_at>?",
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
               VALUES(?,?,?,?,?,?) ON CONFLICT(query_key) DO UPDATE SET
               title=excluded.title, extract=excluded.extract, source_url=excluded.source_url,
               retrieved_at=excluded.retrieved_at, expires_at=excluded.expires_at""",
            (key, title, extract, source_url, current, current + CACHE_TTL_SECONDS),
        )


def retrieve_knowledge(query: str) -> dict | None:
    """Return a fresh cached fact, otherwise fetch and cache a sourced summary."""
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
        return None


_GREETING_RE = re.compile(
    r"^(?:السلام عليكم|السلام عليكو|سلام عليكم|مرحبا|مرحباً|اهلا|أهلا|اهلين|أهلين|هلا|هاي|"
    r"صباح الخير|مساء الخير|ازيك|إزيك|عامل ايه|عامل إيه|كيف حالك|hello|hi|hey|bonjour|hola|hallo)"
    r"[\s!！،,.؟?]*$", re.IGNORECASE,
)


def local_greeting(message: str) -> str | None:
    value = str(message or "").strip()
    if value and len(value) <= 60 and _GREETING_RE.fullmatch(value):
        return "أهلًا وسهلًا! أنا Jon2 AI. كيف أقدر أساعدك؟"
    return None


def looks_like_fact_question(message: str) -> bool:
    value = str(message or "").strip()
    if not value:
        return False
    normalized = _normalize(value)
    if normalized.startswith(("ما اسمي", "اسمي", "من انا", "مين انا", "ماذا قلت", "ايه اللي قلته")):
        return False
    language = detect_query_language(value)
    if "؟" in value or "?" in value or any(mark in value for mark in ("。", "？")):
        return True
    lower = value.lower()
    return any(lower.startswith(prefix.lower()) for prefix in QUESTION_STARTERS.get(language, ()))


def format_knowledge_answer(item: dict) -> str:
    title = str(item.get("title", "Knowledge source")).strip()
    extract = str(item.get("extract", "")).strip()
    source = str(item.get("source_url", "")).strip()
    language = str(item.get("language", "ar"))
    if not extract or not source.startswith("https://"):
        raise ValueError("Knowledge result is incomplete.")
    labels = {
        "ar": ("المصدر", "ملاحظة الترخيص"),
        "fr": ("Source", "Licence"),
        "es": ("Fuente", "Licencia"),
        "de": ("Quelle", "Lizenz"),
        "it": ("Fonte", "Licenza"),
        "pt": ("Fonte", "Licença"),
        "ja": ("出典", "ライセンス"),
        "zh": ("来源", "许可"),
        "ko": ("출처", "라이선스"),
    }
    source_label, license_label = labels.get(language, ("Source", "License"))
    attribution = f"{source_label}: Wikipedia — {source}\n{license_label}: review the source page for attribution and CC BY-SA terms."
    if language == "ar":
        attribution = f"المصدر: ويكيبيديا — {source}\nملاحظة الترخيص: يُرجى مراجعة صفحة المصدر لتفاصيل الإسناد وترخيص المحتوى (CC BY-SA)."
    return f"{title}:\n{extract}\n\n{attribution}"
