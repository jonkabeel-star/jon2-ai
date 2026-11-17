"""Fail-closed rights screening for Open Arabic Books metadata.

This utility reads metadata only (CSV, TSV, or JSONL). It never downloads or
reads book text, never grants Jon2 training approval, and never edits the
private source-approval manifest. Every non-blocked record remains subject to
human and jurisdiction-specific rights review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DATASET_NAME = "Bayanat-Labs/open-arabic-books"
DATASET_VERSION = "0.1.0"
UPSTREAM_DOI = "https://doi.org/10.5878/7rbh-gy93"
REQUIRED_FIELDS = {
    "book_id", "title", "is_translation", "design_license",
    "translation_covered", "original_text_status", "license_decision",
    "license_quote", "license_checked_at", "rights_statement",
    "attribution", "book_url", "source_file_sha256", "upstream_dataset",
    "credits",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_ORIGINAL_STATUSES = {"public-domain", "CC-BY-3.0"}


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _boolean(value):
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True", "TRUE", "yes", "YES"):
        return True
    if value in (0, "0", "false", "False", "FALSE", "no", "NO"):
        return False
    return None


def _credits(value) -> list[dict] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, dict) for item in value):
        return None
    return value


def read_metadata(path: Path) -> list[dict]:
    """Read a metadata-only export; Parquet is intentionally not implicit."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Metadata line {line_number} must be a JSON object.")
            rows.append(row)
        return rows
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle, delimiter=delimiter))
    raise ValueError("Use a metadata-only .csv, .tsv, or .jsonl export. Parquet/text ingestion is not enabled.")


def screen_record(row: dict, *, jurisdiction: str = "EG") -> dict:
    """Return a review-only decision. This function never returns APPROVED."""
    reasons = []
    blockers = []
    missing = sorted(field for field in REQUIRED_FIELDS if field not in row or row[field] in (None, ""))
    if missing:
        blockers.append("missing_required_metadata:" + ",".join(missing))

    is_translation = _boolean(row.get("is_translation"))
    translation_covered = _boolean(row.get("translation_covered"))
    if is_translation is None:
        blockers.append("is_translation_not_boolean")
    if translation_covered is None:
        blockers.append("translation_covered_not_boolean")

    design_license = _text(row.get("design_license")).upper().replace(" ", "")
    if design_license not in {"CC-BY-4.0", "CCBY4.0"}:
        blockers.append("design_license_not_exact_cc_by_4_0")

    original_status = _text(row.get("original_text_status"))
    if original_status not in ALLOWED_ORIGINAL_STATUSES:
        blockers.append("original_text_status_not_in_supported_release_set")

    if is_translation is True and translation_covered is not True:
        blockers.append("arabic_translation_not_explicitly_covered")
    if is_translation is False and translation_covered is True:
        blockers.append("translation_coverage_conflicts_with_translation_flag")

    expected_decision = None
    if is_translation is True and original_status == "public-domain":
        expected_decision = "translation_cc_by_4_original_public_domain"
    elif is_translation is True and original_status == "CC-BY-3.0":
        expected_decision = "translation_cc_by_4_original_cc_by"
    elif is_translation is False and original_status == "public-domain":
        expected_decision = "text_public_domain"
    if expected_decision and _text(row.get("license_decision")) != expected_decision:
        blockers.append("license_decision_does_not_match_book_rights_fields")

    quote = _text(row.get("license_quote"))
    rights_statement = _text(row.get("rights_statement"))
    attribution = _text(row.get("attribution"))
    if not quote:
        blockers.append("missing_original_colophon_quote")
    if not rights_statement:
        blockers.append("missing_rights_statement")
    if not attribution:
        blockers.append("missing_attribution_chain")

    checked_at = _text(row.get("license_checked_at"))
    try:
        date.fromisoformat(checked_at)
    except ValueError:
        blockers.append("invalid_or_missing_license_check_date")

    source_hash = _text(row.get("source_file_sha256"))
    if not SHA256_RE.fullmatch(source_hash):
        blockers.append("invalid_source_file_sha256")

    book_url = _text(row.get("book_url"))
    parsed_url = urlparse(book_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        blockers.append("book_url_not_https")

    upstream = _text(row.get("upstream_dataset"))
    if UPSTREAM_DOI not in upstream:
        blockers.append("unexpected_or_missing_upstream_corpus_reference")

    credit_rows = _credits(row.get("credits"))
    if credit_rows is None:
        blockers.append("credits_not_a_valid_list")
        credit_rows = []
    author_rows = [item for item in credit_rows if item.get("role") == "author"]
    translator_rows = [item for item in credit_rows if item.get("role") == "translator"]
    if not author_rows:
        reasons.append("author_identity_not_resolved_in_credits")
    if is_translation is True and not translator_rows:
        reasons.append("translator_identity_not_resolved_in_credits")
    rights_bearing_roles = {"author", "translator", "editor", "compiler", "foreword"}
    for contributor in credit_rows:
        role = contributor.get("role")
        if role not in rights_bearing_roles:
            continue
        death_year = contributor.get("death_year")
        role_prefix = str(role)
        if death_year in (None, ""):
            reasons.append(f"{role_prefix}_death_year_missing_requires_egyptian_rights_review")
        else:
            try:
                # A 50-year term can still be running for a contributor who died in 1976.
                # This is only a review flag, not a legal determination.
                if int(death_year) >= 1976:
                    reasons.append(f"{role_prefix}_death_year_1976_or_later_requires_egyptian_rights_review")
            except (TypeError, ValueError):
                reasons.append(f"{role_prefix}_death_year_invalid_requires_human_review")

    if original_status == "public-domain":
        reasons.append("publisher_public_domain_statement_is_not_an_egyptian_legal_determination")
    if original_status == "CC-BY-3.0":
        reasons.append("original_text_uses_cc_by_3_0_terms_requiring_separate_review")
    reasons.extend([
        "verify_all_authors_translators_editors_and_other_contributors_rights",
        "verify_cc_by_attribution_and_intended_training_use",
        "native_arabic_quality_and_privacy_review_not_performed",
    ])

    status = "HOLD" if blockers else "HUMAN_REVIEW_REQUIRED"
    return {
        "book_id": _text(row.get("book_id")),
        "title": _text(row.get("title")),
        "is_translation": is_translation,
        "original_text_status": original_status,
        "license_decision": _text(row.get("license_decision")),
        "design_license": _text(row.get("design_license")),
        "book_url": book_url,
        "source_file_sha256": source_hash,
        "jurisdiction": jurisdiction,
        "screening_status": status,
        "training_approval": "NOT_GRANTED",
        "blockers": blockers,
        "human_review_reasons": list(dict.fromkeys(reasons)),
        "attribution": attribution,
        "license_quote": quote,
        "rights_statement": rights_statement,
        "license_checked_at": checked_at,
        "upstream_dataset": upstream,
    }


def screen_rows(rows: list[dict], *, jurisdiction: str = "EG") -> list[dict]:
    seen = set()
    output = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Metadata row {index} is not an object.")
        record = screen_record(row, jurisdiction=jurisdiction)
        book_id = record["book_id"]
        if not book_id:
            record["screening_status"] = "HOLD"
            record["blockers"].append("missing_book_id")
        elif book_id in seen:
            record["screening_status"] = "HOLD"
            record["blockers"].append("duplicate_book_id")
        seen.add(book_id)
        output.append(record)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Screen Open Arabic Books metadata for human rights review; never approve training."
    )
    parser.add_argument("--metadata", required=True, help="Metadata-only CSV, TSV, or JSONL export.")
    parser.add_argument("--output", default="jon2-open-arabic-books-rights-review.jsonl")
    parser.add_argument("--jurisdiction", choices=["EG"], default="EG")
    args = parser.parse_args()

    rows = read_metadata(Path(args.metadata))
    if not rows:
        raise ValueError("Metadata export is empty.")
    results = screen_rows(rows, jurisdiction=args.jurisdiction)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    counts = Counter(record["screening_status"] for record in results)
    summary = {
        "screening_version": 1,
        "dataset": DATASET_NAME,
        "dataset_version": DATASET_VERSION,
        "jurisdiction": args.jurisdiction,
        "metadata_rows": len(results),
        "screening_counts": dict(counts),
        "training_approvals_granted": 0,
        "text_downloaded": False,
        "training_started": False,
        "source_approval_manifest_modified": False,
        "output": str(output),
        "warning": "Screening is not legal advice or training approval. Every non-held record requires human and jurisdiction-specific review.",
    }
    summary_path = output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
