"""Collect a topic-balanced Arabic Wikipedia starter corpus for Jon2 AI.

This writes to a separate output folder so the original starter corpus is preserved.
Wikipedia text is generally CC BY-SA 4.0; verify each article page for exceptions.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://ar.wikipedia.org/w/api.php"
LICENSE_NAME = "CC BY-SA 4.0 (verify each article page for exceptions)"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
USER_AGENT = "Jon2AI/1.0 (https://github.com/jonkabeel-star/jon2-ai; Arabic corpus collection)"

# Broad subject areas. Missing/empty categories are reported and skipped safely.
CATEGORIES = [
    "تصنيف:علوم",
    "تصنيف:تاريخ",
    "تصنيف:جغرافيا",
    "تصنيف:صحة",
    "تصنيف:رياضة",
    "تصنيف:أدب",
    "تصنيف:فنون",
    "تصنيف:تقنية",
    "تصنيف:اقتصاد",
    "تصنيف:تعليم",
    "تصنيف:ثقافة",
    "تصنيف:طبيعة",
]

EXCLUDED_TITLE_PREFIXES = (
    "قائمة ", "قائمة:", "تصنيف:", "بوابة:", "ويكيبيديا:",
    "ملف:", "قالب:", "نقاش:",
)


def fetch_api(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_article_text(value: str) -> str:
    value = value.replace("\r", "\n").replace("\u00a0", " ")
    lines = []
    for raw in value.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or len(line) < 3:
            continue
        if re.fullmatch(r"[\W_\d]+", line, flags=re.UNICODE):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_for_dedup(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def collect_candidates(per_category_limit: int) -> dict[int, dict]:
    candidates: dict[int, dict] = {}
    for category in CATEGORIES:
        continuation = {}
        category_count = 0
        while category_count < per_category_limit:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmtype": "page",
                "cmnamespace": 0,
                "cmlimit": min(100, per_category_limit - category_count),
                "format": "json",
            }
            params.update(continuation)
            try:
                payload = fetch_api(params)
            except Exception as exc:
                print(f"Skipping category {category}: {exc}", flush=True)
                break

            members = payload.get("query", {}).get("categorymembers", [])
            if not members and not continuation:
                print(f"Category has no direct article members: {category}", flush=True)

            for member in members:
                page_id = member.get("pageid")
                if not page_id:
                    continue
                title = member.get("title", "")
                if title.startswith(EXCLUDED_TITLE_PREFIXES):
                    continue
                if page_id not in candidates:
                    candidates[page_id] = {
                        "pageid": page_id,
                        "title": title,
                        "categories": set(),
                    }
                candidates[page_id]["categories"].add(category)
                category_count += 1
                if category_count >= per_category_limit:
                    break

            continuation = payload.get("continue") or {}
            if not continuation or not members:
                break

        print(
            f"Category scan: {category} — {category_count} candidate articles",
            flush=True,
        )
    return candidates


def collect_corpus(
    output_dir: Path,
    target_chars: int = 250_000,
    max_pages: int = 4000,
    per_category_limit: int = 250,
    pause_seconds: float = 0.2,
) -> tuple[int, int]:
    if target_chars < 100_000:
        raise ValueError("target_chars must be at least 100,000.")

    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = output_dir / "wikipedia_ar_diverse_cc_by_sa.txt"
    manifest_path = output_dir / "wikipedia_ar_diverse_sources.json"

    print("Collecting article candidates from varied Arabic Wikipedia categories...", flush=True)
    candidates = collect_candidates(per_category_limit)
    candidate_list = list(candidates.values())
    random.Random(20261031).shuffle(candidate_list)
    print(f"Unique candidate articles found: {len(candidate_list)}", flush=True)

    articles = []
    records = []
    seen_text = set()
    total_chars = 0
    requests_made = 0
    consecutive_errors = 0

    for candidate in candidate_list:
        if total_chars >= target_chars or requests_made >= max_pages:
            break

        try:
            payload = fetch_api({
                "action": "query",
                "pageids": candidate["pageid"],
                "prop": "extracts|info|pageprops",
                "explaintext": 1,
                "inprop": "url",
                "format": "json",
                "formatversion": 2,
            })
            requests_made += 1
            consecutive_errors = 0
        except Exception as exc:
            requests_made += 1
            consecutive_errors += 1
            print(f"Article API issue ({consecutive_errors}/5): {exc}", flush=True)
            if consecutive_errors >= 5:
                print("Stopping after five consecutive API errors.", flush=True)
                break
            time.sleep(3)
            continue

        pages = payload.get("query", {}).get("pages", [])
        if not pages:
            continue
        page = pages[0]
        if "missing" in page or "disambiguation" in page.get("pageprops", {}):
            continue

        text = clean_article_text(page.get("extract", ""))
        normalized = normalize_for_dedup(text)
        if len(text) < 500 or not normalized or normalized in seen_text:
            continue

        seen_text.add(normalized)
        remaining = target_chars - total_chars
        selected = text[:remaining]
        if len(selected) < 300:
            break

        title = page.get("title", candidate["title"])
        url = page.get("fullurl") or (
            "https://ar.wikipedia.org/wiki/"
            + urllib.parse.quote(title.replace(" ", "_"))
        )
        article_categories = sorted(candidate["categories"])
        articles.append(selected)
        records.append({
            "pageid": candidate["pageid"],
            "title": title,
            "url": url,
            "categories": article_categories,
            "license": LICENSE_NAME,
            "license_url": LICENSE_URL,
            "source": "Arabic Wikipedia / MediaWiki API",
            "modified": (
                "Plain-text extraction, whitespace normalization, short/noisy-line "
                "removal, exact-text deduplication; final selected article may be "
                "truncated to target size."
            ),
        })
        total_chars += len(selected) + 2

        if requests_made % 25 == 0:
            print(
                f"Progress: {requests_made} article requests, "
                f"{len(records)} usable articles, {total_chars:,} characters.",
                flush=True,
            )
        time.sleep(pause_seconds)

    # Save partial results too; a failed/incomplete run must not discard progress.
    corpus_path.write_text("\n\n".join(articles) + ("\n" if articles else ""), encoding="utf-8")
    manifest = {
        "dataset": "Jon2 diverse Arabic Wikipedia starter corpus",
        "language": "Arabic (Modern Standard Arabic and mixed article registers)",
        "source": "https://ar.wikipedia.org/",
        "collection_method": "Balanced candidate sampling from multiple subject categories, then deterministic shuffle",
        "categories_requested": CATEGORIES,
        "categories_used": sorted({c for item in records for c in item["categories"]}),
        "candidate_count": len(candidate_list),
        "license": LICENSE_NAME,
        "license_url": LICENSE_URL,
        "attribution": "Each article title, URL, and category is recorded below. The linked page history identifies contributors.",
        "changes": "Plain-text extraction, whitespace normalization, short/noisy-line removal, exact-text deduplication, and possible truncation of the final selected article.",
        "collected_characters_including_separators": total_chars,
        "article_count": len(records),
        "warning": "Verify article-specific notices and applicable rights before commercial distribution. CC BY-SA requires attribution and share-alike for adapted material; this script does not provide legal advice.",
        "articles": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Saved {total_chars:,} characters from {len(records)} articles.", flush=True)
    print(f"Corpus: {corpus_path}", flush=True)
    print(f"Sources: {manifest_path}", flush=True)
    if total_chars < target_chars:
        print(
            f"NOTE: Target was {target_chars:,}; partial dataset has been saved. "
            "Review category coverage before deciding whether to collect more.",
            flush=True,
        )
    return total_chars, len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="training_data/diverse")
    parser.add_argument("--target-chars", type=int, default=250_000)
    parser.add_argument("--max-pages", type=int, default=4000)
    parser.add_argument("--per-category-limit", type=int, default=250)
    args = parser.parse_args()
    collect_corpus(
        Path(args.output_dir),
        args.target_chars,
        args.max_pages,
        args.per_category_limit,
    )


if __name__ == "__main__":
    main()
