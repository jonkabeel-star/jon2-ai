#!/usr/bin/env python3
"""Aggregate-only audit for a plain-text Jon2 training corpus.

Never prints source text. This is a structural report, not a copyright or
privacy clearance decision.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
CONTACT_RE = re.compile(r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?:\+?\d[\d\s().-]{7,}\d))")

def audit_text(path: str | Path) -> dict:
    p = Path(path)
    raw = p.read_bytes()
    text = raw.decode("utf-8-sig")
    paragraphs = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n\s*\n", text)]
    paragraphs = [x for x in paragraphs if x]
    unique = set(paragraphs)
    chars = len(text)
    arabic_chars = len(ARABIC_RE.findall(text))
    return {
        "file_name": p.name,
        "file_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "characters_including_whitespace": chars,
        "non_whitespace_characters": len(re.sub(r"\s", "", text)),
        "arabic_characters": arabic_chars,
        "arabic_share_of_non_whitespace": round(
            arabic_chars / max(1, len(re.sub(r"\s", "", text))), 4
        ),
        "paragraph_count": len(paragraphs),
        "unique_paragraph_count": len(unique),
        "duplicate_paragraph_count": len(paragraphs) - len(unique),
        "paragraphs_under_80_chars": sum(len(x) < 80 for x in paragraphs),
        "paragraphs_over_3000_chars": sum(len(x) > 3000 for x in paragraphs),
        "possible_contact_detail_matches": len(CONTACT_RE.findall(text)),
        "empty_file": not bool(text.strip()),
        "note": "Structural audit only; verify page-level license, attribution, share-alike obligations, privacy, and intended model-training use separately."
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    try:
        report = audit_text(args.file)
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"audit_error": type(exc).__name__}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["empty_file"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
