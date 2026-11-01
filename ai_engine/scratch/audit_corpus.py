"""Audit private Jon2 JSONL datasets without printing their contents.

Supported records:
- {"messages": [{"role": "user"|"assistant", "content": "..."}]}
- {"prompt": "...", "response": "..."}
- {"instruction": "...", "input": "...", "output": "..."}
- {"question": "...", "answer": "..."}
The report contains aggregate counts only. No source text is written to disk.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
SPACE_RE = re.compile(r"\s+")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return SPACE_RE.sub(" ", value).strip()


def extract_record(record: Any) -> tuple[str, str]:
    if not isinstance(record, dict):
        raise ValueError("each JSONL row must be an object")

    messages = record.get("messages")
    if isinstance(messages, list):
        users, assistants = [], []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).lower()
            text = message.get("content", message.get("text", ""))
            if not isinstance(text, str):
                continue
            if role in {"user", "human"}:
                users.append(text.strip())
            elif role in {"assistant", "bot"}:
                assistants.append(text.strip())
        return "\n".join(filter(None, users)), "\n".join(filter(None, assistants))

    pairs = (
        ("prompt", "response"),
        ("instruction", "output"),
        ("question", "answer"),
        ("user", "assistant"),
    )
    for user_key, assistant_key in pairs:
        user_text = record.get(user_key, "")
        assistant_text = record.get(assistant_key, "")
        if isinstance(user_text, str) and isinstance(assistant_text, str):
            if user_text.strip() or assistant_text.strip():
                extra = record.get("input", "")
                if user_key == "instruction" and isinstance(extra, str) and extra.strip():
                    user_text = user_text + "\n" + extra
                return user_text.strip(), assistant_text.strip()

    raise ValueError("unsupported schema; expected messages or a supported prompt/response pair")


def read_jsonl(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    records: list[tuple[str, str]] = []
    errors: list[str] = []
    if not path.is_file():
        return records, [f"file not found: {path}"]
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                records.append(extract_record(json.loads(raw)))
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"line {line_number}: {exc}")
    return records, errors


def audit_split(name: str, path: Path) -> tuple[dict[str, Any], set[str], list[str]]:
    records, errors = read_jsonl(path)
    fingerprints: set[str] = set()
    duplicates = 0
    empty_user = empty_assistant = 0
    user_chars = assistant_chars = arabic_chars = 0
    privacy_flags = 0

    for user_text, assistant_text in records:
        user_norm, assistant_norm = normalize(user_text), normalize(assistant_text)
        if not user_norm:
            empty_user += 1
        if not assistant_norm:
            empty_assistant += 1
        fingerprint = user_norm + "\u241f" + assistant_norm
        if fingerprint in fingerprints:
            duplicates += 1
        fingerprints.add(fingerprint)
        user_chars += len(user_text)
        assistant_chars += len(assistant_text)
        arabic_chars += len(ARABIC_RE.findall(user_text + assistant_text))
        if EMAIL_RE.search(user_text + " " + assistant_text) or PHONE_RE.search(user_text + " " + assistant_text):
            privacy_flags += 1

    total_chars = user_chars + assistant_chars
    report = {
        "split": name,
        "file": str(path),
        "records": len(records),
        "user_characters": user_chars,
        "assistant_characters": assistant_chars,
        "total_characters": total_chars,
        "average_assistant_characters": round(assistant_chars / len(records), 2) if records else 0,
        "arabic_character_share_percent": round(100 * arabic_chars / total_chars, 2) if total_chars else 0,
        "duplicate_records": duplicates,
        "empty_user_records": empty_user,
        "empty_assistant_records": empty_assistant,
        "possible_private_contact_records": privacy_flags,
        "parse_errors": len(errors),
    }
    return report, fingerprints, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate-only audit for private Jon2 JSONL data.")
    parser.add_argument("--train", type=Path, required=True, help="Path to training JSONL")
    parser.add_argument("--test", type=Path, required=True, help="Path to held-out test JSONL")
    parser.add_argument("--min-train-records", type=int, default=100, help="Minimum training records for a green readiness check")
    parser.add_argument("--min-train-characters", type=int, default=100_000, help="Minimum training characters for a green readiness check")
    args = parser.parse_args()

    train, train_fingerprints, train_errors = audit_split("train", args.train)
    test, test_fingerprints, test_errors = audit_split("test", args.test)
    overlap = len(train_fingerprints & test_fingerprints)

    checks = {
        "train_records_minimum": train["records"] >= args.min_train_records,
        "train_characters_minimum": train["total_characters"] >= args.min_train_characters,
        "both_splits_parse_cleanly": train["parse_errors"] == 0 and test["parse_errors"] == 0,
        "no_train_test_exact_overlap": overlap == 0,
        "no_empty_answers": train["empty_assistant_records"] == 0 and test["empty_assistant_records"] == 0,
        "no_duplicate_records": train["duplicate_records"] == 0 and test["duplicate_records"] == 0,
        "manual_privacy_review_required": train["possible_private_contact_records"] == 0 and test["possible_private_contact_records"] == 0,
    }
    result = {
        "tool": "Jon2 private corpus audit",
        "privacy": "aggregate counts only; source text is never printed or copied",
        "train": train,
        "test": test,
        "exact_train_test_overlap": overlap,
        "checks": checks,
        "training_ready": all(checks.values()),
        "note": "A green audit is a data-quality gate, not proof that the model will learn useful language.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if train_errors or test_errors:
        print("\nParse details:", file=sys.stderr)
        for error in (train_errors + test_errors)[:20]:
            print(error, file=sys.stderr)
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
