"""Privacy-aware quality audit for proposed Jon2 text corpora.

Reports structural signals only. It does not decide licensing, factual quality,
or semantic suitability, and never prints matched personal-data values.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟。])\s+")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}


def normalize_line(line: str) -> str:
    """Normalize whitespace and Unicode composition for duplicate detection only."""
    return " ".join(unicodedata.normalize("NFC", line).casefold().split())


def phone_like_matches(text: str) -> list[str]:
    """Return phone-like strings while excluding valid ISO calendar dates.

    Date stamps such as 2026-11-04 match the broad phone heuristic but are not
    contact details. Keep the heuristic conservative and report counts only.
    """
    matches = []
    for candidate in PHONE.findall(text):
        value = candidate.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                date.fromisoformat(value)
            except ValueError:
                pass
            else:
                continue
        matches.append(candidate)
    return matches


def analyze_text(text: str, source_name: str = "text") -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized = [normalize_line(line) for line in lines]
    duplicate_counts = Counter(normalized)
    duplicate_line_groups = sum(1 for count in duplicate_counts.values() if count > 1)
    duplicate_excess_lines = sum(count - 1 for count in duplicate_counts.values() if count > 1)

    sentences = [
        part.strip()
        for line in lines
        for part in SENTENCE_SPLIT.split(line)
        if part.strip()
    ]
    sentence_lengths = [len(sentence) for sentence in sentences]
    line_lengths = [len(line) for line in lines]
    chars = len(text)
    letters_count = sum(1 for ch in text if ch.isalpha())
    arabic_count = sum(1 for ch in text if ch.isalpha() and "\u0600" <= ch <= "\u06ff")
    latin_count = sum(1 for ch in text if ch.isalpha() and ("A" <= ch <= "Z" or "a" <= ch <= "z"))
    controls = [
        ch for ch in text
        if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t"
    ]
    replacement_count = text.count("\ufffd")
    zero_width_count = sum(text.count(ch) for ch in ZERO_WIDTH)
    phone_matches = phone_like_matches(text)

    def distribution(values: list[int]) -> dict:
        if not values:
            return {"count": 0, "min": 0, "median": 0, "max": 0, "mean": 0.0}
        ordered = sorted(values)
        n = len(ordered)
        median = (
            ordered[n // 2] if n % 2
            else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
        )
        return {
            "count": n,
            "min": ordered[0],
            "median": median,
            "max": ordered[-1],
            "mean": round(sum(ordered) / n, 2),
        }

    return {
        "source": source_name,
        "characters": chars,
        "non_empty_lines": len(lines),
        "sentences_estimated": len(sentences),
        "line_length_characters": distribution(line_lengths),
        "sentence_length_characters": distribution(sentence_lengths),
        "language_mix": {
            "letters_total": letters_count,
            "arabic_letters": arabic_count,
            "latin_letters": latin_count,
            "arabic_percentage_of_letters": round(100 * arabic_count / letters_count, 3) if letters_count else 0.0,
            "latin_percentage_of_letters": round(100 * latin_count / letters_count, 3) if letters_count else 0.0,
        },
        "duplicate_lines": {
            "normalized_duplicate_groups": duplicate_line_groups,
            "excess_duplicate_lines": duplicate_excess_lines,
        },
        "integrity_signals": {
            "unicode_replacement_characters": replacement_count,
            "unexpected_control_characters": len(controls),
            "zero_width_or_bom_characters": zero_width_count,
        },
        "privacy_review_signals": {
            "email_like_matches": len(EMAIL.findall(text)),
            "url_matches": len(URL.findall(text)),
            "phone_like_matches": len(phone_matches),
            "note": "Counts only; matched values are never included in this report. Human review is still required.",
        },
        "warnings": _warnings(
            chars, duplicate_excess_lines, replacement_count,
            len(controls), zero_width_count,
            len(EMAIL.findall(text)), len(phone_matches),
        ),
    }


def _warnings(chars, duplicates, replacements, controls, zero_width, emails, phones):
    warnings = []
    if chars == 0:
        warnings.append("Source is empty.")
    if duplicates:
        warnings.append(f"{duplicates} excess line(s) duplicate another normalized line.")
    if replacements:
        warnings.append(f"{replacements} Unicode replacement character(s) may indicate decoding damage.")
    if controls:
        warnings.append(f"{controls} unexpected control character(s) found.")
    if zero_width:
        warnings.append(f"{zero_width} zero-width/BOM character(s) found; inspect before normalization.")
    if emails or phones:
        warnings.append("Possible personal contact information detected; inspect privately and remove unless explicitly authorized.")
    return warnings


def analyze_directory(data_dir: Path) -> dict:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")
    files = sorted(path for path in data_dir.rglob("*.txt") if path.is_file())
    if not files:
        raise ValueError(f"No .txt files found in {data_dir}")

    reports = []
    root = data_dir.resolve()
    for path in files:
        # Do not follow a corpus-file symlink outside the selected workspace.
        # The inventory and training approval gates enforce the same boundary.
        if not path.resolve().is_relative_to(root):
            raise PermissionError(f"Corpus source resolves outside data directory: {path}")
        raw = path.read_bytes()
        decoded = raw.decode("utf-8", errors="strict")
        reports.append(analyze_text(decoded, path.relative_to(data_dir).as_posix()))

    combined_text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    combined = analyze_text(combined_text, "combined")
    return {
        "report_version": 1,
        "audit_type": "structural_quality_and_privacy_signals",
        "files": reports,
        "combined": combined,
        "file_count": len(files),
        "limitations": [
            "Sentence splitting is heuristic and language-dependent.",
            "Duplicate detection is exact after NFC and whitespace normalization; paraphrases are not detected.",
            "Email and phone patterns are review signals, not a complete personal-data detector.",
            "This audit cannot determine copyright, consent, factual accuracy, or semantic quality.",
            "No source text or matched personal-data values are copied into the report.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit corpus quality and privacy signals.")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = analyze_directory(Path(args.data))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
