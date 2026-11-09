"""Privacy-aware intake audit for proposed Jon2 Arabic text sources.

This tool reads a local candidate only. It does not download, approve, copy,
normalize, or add data to any training corpus. Rights approval remains a
separate human-reviewed process enforced by data_rights.rights_gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}


def _documents(path: Path, decoded: str) -> Iterable[str]:
    if path.suffix.lower() == ".txt":
        yield from (line.strip() for line in decoded.splitlines() if line.strip())
        return
    if path.suffix.lower() != ".jsonl":
        raise ValueError("Only UTF-8 .txt and .jsonl candidates are supported.")
    for number, line in enumerate(decoded.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSONL record at line {number}.") from exc
        if not isinstance(record, dict) or not isinstance(record.get("text"), str):
            raise ValueError(f"JSONL record at line {number} must contain a string 'text' field.")
        value = record["text"].strip()
        if value:
            yield value


def audit_candidate(candidate: str | Path) -> dict:
    path = Path(candidate)
    if path.is_symlink():
        raise ValueError("Candidate file cannot be a symlink.")
    if not path.is_file():
        raise FileNotFoundError("Candidate must be an existing regular file.")
    if path.suffix.lower() not in {".txt", ".jsonl"}:
        raise ValueError("Only UTF-8 .txt and .jsonl candidates are supported.")
    raw = path.read_bytes()
    decoded = raw.decode("utf-8", errors="strict")
    documents = list(_documents(path, decoded))

    normalized = [
        " ".join(unicodedata.normalize("NFC", item).casefold().split())
        for item in documents
    ]
    counts = Counter(normalized)
    duplicate_groups = sum(1 for count in counts.values() if count > 1)
    duplicate_excess = sum(count - 1 for count in counts.values() if count > 1)

    letters = [char for char in decoded if char.isalpha()]
    arabic_letters = [char for char in letters if unicodedata.name(char, "").startswith("ARABIC ")]
    latin_letters = [char for char in letters if "a" <= char.lower() <= "z"]
    phone_matches = []
    for match in PHONE_RE.findall(decoded):
        value = match.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            continue
        phone_matches.append(match)

    return {
        "report_version": 1,
        "candidate_file": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "format": path.suffix.lower().lstrip("."),
        "bytes": len(raw),
        "characters": len(decoded),
        "documents": len(documents),
        "nonempty_lines": sum(1 for line in decoded.splitlines() if line.strip()),
        "language_signals": {
            "letters": len(letters),
            "arabic_letters": len(arabic_letters),
            "latin_letters": len(latin_letters),
            "arabic_percentage_of_letters": round(100 * len(arabic_letters) / len(letters), 2) if letters else 0.0,
        },
        "duplicate_signals": {
            "normalized_duplicate_groups": duplicate_groups,
            "excess_duplicate_documents": duplicate_excess,
        },
        "privacy_signals": {
            "email_like_matches": len(EMAIL_RE.findall(decoded)),
            "url_matches": len(URL_RE.findall(decoded)),
            "phone_like_matches": len(phone_matches),
            "matched_values_included": False,
        },
        "integrity_signals": {
            "replacement_characters": decoded.count("\ufffd"),
            "unexpected_control_characters": sum(
                1 for char in decoded
                if unicodedata.category(char) == "Cc" and char not in "\n\r\t"
            ),
            "zero_width_or_bom_characters": sum(decoded.count(char) for char in ZERO_WIDTH),
        },
        "rights_review": {
            "status": "NOT_REVIEWED",
            "human_approval_required": True,
            "training_eligible": False,
            "note": "This audit does not establish ownership, licensing, consent, or permission for model training.",
        },
        "side_effects": {
            "source_modified": False,
            "training_corpus_modified": False,
            "network_access": False,
            "training_started": False,
        },
        "warnings": _warnings(
            len(documents), duplicate_excess, decoded.count("\ufffd"),
            len(EMAIL_RE.findall(decoded)), len(phone_matches),
        ),
    }


def _warnings(documents: int, duplicates: int, replacements: int, emails: int, phones: int) -> list[str]:
    warnings = []
    if documents == 0:
        warnings.append("Candidate contains no non-empty documents.")
    if duplicates:
        warnings.append(f"{duplicates} exact normalized duplicate document(s) should be reviewed.")
    if replacements:
        warnings.append(f"{replacements} Unicode replacement character(s) may indicate decoding damage.")
    if emails or phones:
        warnings.append("Possible personal contact details detected; review privately and remove unless explicitly authorized.")
    return warnings



def _ensure_distinct_paths(candidate: str | Path, output: str | Path) -> None:
    """Prevent a report destination from overwriting the candidate source."""
    source_path = Path(candidate)
    output_path = Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("Report output must not be the candidate source file.")
    if source_path.exists() and output_path.exists() and os.path.samefile(source_path, output_path):
        raise ValueError("Report output must not be the candidate source file.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a local Jon2 data candidate without approving or importing it.")
    parser.add_argument("--candidate", required=True, help="Path to a local .txt or .jsonl file.")
    parser.add_argument("--output", default="", help="Optional JSON report path.")
    args = parser.parse_args()
    if args.output:
        _ensure_distinct_paths(args.candidate, args.output)
    report = audit_candidate(args.candidate)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        print(f"Candidate audit report written to {destination}")
    else:
        print(rendered, end="")
    print(
        f"Candidate: {report['documents']} documents, {report['characters']:,} characters; "
        f"rights={report['rights_review']['status']}; training_eligible=false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
