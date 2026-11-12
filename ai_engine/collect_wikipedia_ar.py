"""Collect Arabic Wikipedia extracts into a private, unapproved quarantine.

This collector never writes into the approved training-data directory and never
creates or changes a source-approval record. Every collected page remains
ineligible for training until a human completes a separate rights, privacy,
quality, and intended-use review.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://ar.wikipedia.org/w/api.php"
LICENSE_NAME = "CC BY-SA 4.0 (verify each article page and applicable notices)"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
USER_AGENT = "Jon2AI/1.1 (https://github.com/jonkabeel-star/jon2-ai; Arabic corpus collection)"
DEFAULT_OUTPUT_DIR = "private-corpus-quarantine/wikipedia_ar"
QUARANTINE_STATUS = "QUARANTINED_NOT_APPROVED"


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


def fetch_batch(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _assert_quarantine_destination(output_dir: Path) -> None:
    destination = output_dir.resolve()
    candidates = (Path("ai_engine/training_data"), Path("training_data"))
    for candidate in candidates:
        training_dir = candidate.resolve()
        if destination == training_dir or training_dir in destination.parents:
            raise ValueError(
                "Wikipedia collection must stay outside the approved training-data "
                "directory. Use the private quarantine destination instead."
            )


def collect_corpus(
    output_dir: Path,
    target_chars: int = 130_000,
    max_pages: int = 3000,
    pause_seconds: float = 0.25,
) -> tuple[int, int]:
    if target_chars < 100_000:
        raise ValueError("target_chars must be at least 100,000.")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    _assert_quarantine_destination(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = output_dir / "wikipedia_ar_QUARANTINED_NOT_FOR_TRAINING.txt"
    manifest_path = output_dir / "wikipedia_ar_quarantine_manifest.json"

    base_params = {
        "action": "query",
        "generator": "allpages",
        "gapnamespace": 0,
        "gapfilterredir": "nonredirects",
        "gapfrom": "أ",
        "gaplimit": 1,
        "prop": "extracts|info|revisions",
        "exlimit": 1,
        "explaintext": 1,
        "inprop": "url",
        "rvprop": "ids|timestamp",
        "rvlimit": 1,
        "format": "json",
        "formatversion": 2,
    }

    continuation = {}
    seen_pages: set[int] = set()
    seen_text: set[str] = set()
    records = []
    articles = []
    total_chars = 0
    requests_made = 0
    network_errors = 0

    while total_chars < target_chars and requests_made < max_pages:
        params = {**base_params, **continuation}
        try:
            payload = fetch_batch(params)
            network_errors = 0
        except Exception as exc:
            network_errors += 1
            print(f"Network/API issue ({network_errors}/5): {exc}", flush=True)
            if network_errors >= 5:
                raise RuntimeError(
                    "Stopped after 5 consecutive network/API errors."
                ) from exc
            time.sleep(5)
            continue

        requests_made += 1
        warnings = payload.get("warnings", {})
        if warnings:
            print("Wikipedia API warning: " + json.dumps(warnings, ensure_ascii=False), flush=True)

        pages = payload.get("query", {}).get("pages", [])
        for page in pages:
            page_id = page.get("pageid")
            if not page_id or page_id in seen_pages:
                continue
            seen_pages.add(page_id)

            text = clean_article_text(page.get("extract", ""))
            normalized = normalize_for_dedup(text)
            if len(text) < 500 or not normalized or normalized in seen_text:
                continue

            seen_text.add(normalized)
            remaining = target_chars - total_chars
            selected = text[:remaining]
            if len(selected) < 300:
                break

            title = page.get("title", "Untitled")
            url = page.get("fullurl") or (
                "https://ar.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            )
            revisions = page.get("revisions") or []
            revision = revisions[0] if revisions else {}
            articles.append(selected)
            records.append({
                "pageid": page_id,
                "title": title,
                "url": url,
                "revision_id": revision.get("revid"),
                "revision_timestamp": revision.get("timestamp"),
                "license": LICENSE_NAME,
                "license_url": LICENSE_URL,
                "source": "Arabic Wikipedia / MediaWiki API",
                "status": QUARANTINE_STATUS,
                "training_eligible": False,
                "commercial_use_eligible": False,
                "human_rights_review_required": True,
                "changes": (
                    "Plain-text extraction, whitespace normalization, "
                    "short/noisy-line removal, duplicate removal; "
                    "the final selected article may be truncated."
                ),
            })
            total_chars += len(selected) + 2

        continuation = payload.get("continue") or {}
        if requests_made % 25 == 0:
            print(
                f"Progress: {requests_made} API requests, "
                f"{len(records)} usable articles, {total_chars:,} characters.",
                flush=True,
            )
        if not continuation:
            break
        if total_chars < target_chars:
            time.sleep(pause_seconds)

    corpus_path.write_text("\n\n".join(articles) + "\n", encoding="utf-8")
    manifest = {
        "dataset": "Jon2 Arabic Wikipedia quarantined research candidate",
        "language": "Arabic (mixed article registers; dialect not classified)",
        "source": "https://ar.wikipedia.org/",
        "license": LICENSE_NAME,
        "license_url": LICENSE_URL,
        "status": QUARANTINE_STATUS,
        "training_eligible": False,
        "commercial_use_eligible": False,
        "approval_created": False,
        "approval_manifest_modified": False,
        "attribution": (
            "Each article title, URL, page ID, and available revision metadata "
            "is recorded below. Article histories identify contributors."
        ),
        "changes": (
            "Plain-text extraction, whitespace normalization, removal of "
            "short/noisy lines, exact-page/text deduplication, and possible "
            "truncation of the final selected article."
        ),
        "collected_characters_including_separators": total_chars,
        "article_count": len(records),
        "warning": (
            "This corpus is quarantined and MUST NOT be used for training or "
            "commercial deployment. Review article-specific notices, attribution, "
            "share-alike obligations, privacy, factual quality, and intended model "
            "use before any separate explicit owner approval. This manifest is "
            "provenance metadata, not a training approval."
        ),
        "articles": records,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Quarantined {total_chars:,} characters from {len(records):,} "
        "Arabic Wikipedia pages. NOT APPROVED FOR TRAINING.",
        flush=True,
    )
    print(
        "Files: wikipedia_ar_QUARANTINED_NOT_FOR_TRAINING.txt and "
        "wikipedia_ar_quarantine_manifest.json",
        flush=True,
    )
    if total_chars < target_chars:
        raise RuntimeError(
            f"Saved a partial quarantined corpus of {total_chars:,} characters "
            f"from {len(records):,} articles after {requests_made:,} API requests. "
            f"Target is {target_chars:,}; increase --max-pages and rerun."
        )
    return total_chars, len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--target-chars", type=int, default=130_000)
    parser.add_argument("--max-pages", type=int, default=3000)
    args = parser.parse_args()
    collect_corpus(Path(args.output_dir), args.target_chars, args.max_pages)


if __name__ == "__main__":
    main()
