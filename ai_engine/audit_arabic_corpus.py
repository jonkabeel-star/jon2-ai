"""Offline, read-only corpus audit for pre-split Jon2 Arabic JSONL data.

This tool never downloads data, changes source files, approves rights, or trains.
It emits aggregate diagnostics only and never copies raw text into the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-z]")
REQUIRED_SPLITS = ("train", "validation", "test")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u0640", "")
    return " ".join(value.split())


def content_hash(value: str) -> str:
    return hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path, split: str, mode: str) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{split}:{line_number}: invalid JSONL ({exc.msg})") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{split}:{line_number}: each record must be a JSON object")
            if mode == "text":
                text = row.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError(f"{split}:{line_number}: text record needs non-empty 'text'")
            else:
                messages = row.get("messages")
                if not isinstance(messages, list) or len(messages) < 2:
                    raise ValueError(f"{split}:{line_number}: dialogue needs at least two messages")
                roles = []
                for message in messages:
                    if not isinstance(message, dict):
                        raise ValueError(f"{split}:{line_number}: invalid message object")
                    role, content = message.get("role"), message.get("content")
                    if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                        raise ValueError(f"{split}:{line_number}: invalid role/content")
                    roles.append(role)
                if roles[0] != "user" or roles[-1] != "assistant":
                    raise ValueError(f"{split}:{line_number}: dialogue must start with user and end with assistant")
                if any(left == right for left, right in zip(roles, roles[1:])):
                    raise ValueError(f"{split}:{line_number}: dialogue roles must alternate")
            rows.append(row)
    return rows


def _record_text(row: dict, mode: str) -> str:
    if mode == "text":
        return row["text"]
    return "\n".join(message["content"] for message in row["messages"])


def audit_splits(split_paths: dict[str, Path], mode: str = "text") -> dict:
    if mode not in {"text", "dialogue"}:
        raise ValueError("mode must be 'text' or 'dialogue'")
    if set(split_paths) != set(REQUIRED_SPLITS):
        raise ValueError("exactly train, validation, and test split paths are required")

    records = {name: _read_jsonl(Path(split_paths[name]), name, mode) for name in REQUIRED_SPLITS}
    hashes: dict[str, dict[str, list[int]]] = {}
    group_splits: dict[str, set[str]] = {}
    split_stats = {}
    privacy_hits = 0
    no_arabic = 0
    total_arabic_chars = 0
    total_latin_chars = 0

    for split, rows in records.items():
        split_hashes: Counter = Counter()
        chars = 0
        for index, row in enumerate(rows):
            value = _record_text(row, mode)
            digest = content_hash(value)
            split_hashes[digest] += 1
            hashes.setdefault(digest, {}).setdefault(split, []).append(index)
            chars += len(value)
            arabic_count = len(ARABIC_RE.findall(value))
            total_arabic_chars += arabic_count
            total_latin_chars += len(LATIN_RE.findall(value))
            if arabic_count == 0:
                no_arabic += 1
            if EMAIL_RE.search(value) or PHONE_RE.search(value):
                privacy_hits += 1
            group = row.get("conversation_id") or row.get("document_id") or row.get("group_id")
            if group is not None:
                if not isinstance(group, (str, int)) or not str(group).strip():
                    raise ValueError(f"{split}:{index + 1}: invalid group identifier")
                group_splits.setdefault(str(group), set()).add(split)
        split_stats[split] = {
            "records": len(rows),
            "characters": chars,
            "within_split_duplicate_records": sum(count - 1 for count in split_hashes.values() if count > 1),
        }

    cross_split_duplicates = []
    for digest, by_split in hashes.items():
        if len(by_split) > 1:
            cross_split_duplicates.append({
                "sha256": digest,
                "splits": sorted(by_split),
                "record_counts": {split: len(indices) for split, indices in by_split.items()},
            })
    group_leakage = sorted(group for group, names in group_splits.items() if len(names) > 1)
    duplicate_count = sum(item["within_split_duplicate_records"] for item in split_stats.values())

    blockers = []
    if any(not records[name] for name in REQUIRED_SPLITS):
        blockers.append("one_or_more_splits_are_empty")
    if cross_split_duplicates:
        blockers.append("exact_normalized_content_leakage_across_splits")
    if group_leakage:
        blockers.append("conversation_or_document_group_leakage_across_splits")
    if privacy_hits:
        blockers.append("possible_personal_data_requires_manual_review")
    if no_arabic:
        blockers.append("records_without_arabic_script_require_manual_language_review")
    if duplicate_count:
        blockers.append("within_split_exact_duplicates_found")

    return {
        "report_version": 1,
        "mode": mode,
        "split_stats": split_stats,
        "total_records": sum(item["records"] for item in split_stats.values()),
        "script_counts": {
            "arabic_characters": total_arabic_chars,
            "latin_characters": total_latin_chars,
            "dialect_classification": "NOT_INFERRED_REQUIRES_HUMAN_ANNOTATION",
        },
        "quality_flags": {
            "within_split_duplicate_records": duplicate_count,
            "cross_split_duplicate_groups": len(cross_split_duplicates),
            "group_leakage_count": len(group_leakage),
            "possible_pii_records": privacy_hits,
            "records_without_arabic_script": no_arabic,
        },
        "leakage_details": {
            "cross_split_duplicate_hashes": cross_split_duplicates,
            "group_ids_across_splits": group_leakage,
        },
        "blockers": blockers,
        "ready_for_training": False,
        "human_review": {
            "required": True,
            "rights_reviewed": False,
            "privacy_reviewed": False,
            "language_and_dialect_reviewed": False,
            "quality_reviewed": False,
            "reviewer": None,
            "review_date": None,
            "approved": False,
        },
        "warning": (
            "Diagnostic only; does not establish copyright permission, dialect authenticity, "
            "semantic quality, or training readiness. It never approves data or starts training."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of existing train/validation/test Arabic JSONL files.")
    parser.add_argument("--mode", choices=("text", "dialogue"), required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_splits(
        {"train": args.train, "validation": args.validation, "test": args.test},
        mode=args.mode,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "total_records": report["total_records"],
        "quality_flags": report["quality_flags"],
        "blockers": report["blockers"],
        "ready_for_training": report["ready_for_training"],
    }, ensure_ascii=False))
    return 0 if not report["blockers"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
