"""Audit Jon2 training text without importing ML dependencies.

This checks formatting and obvious data-quality issues. It does not approve
copyright, privacy, or commercial-use rights; see DATASET_REGISTER.md.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


def clean_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="strict").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def audit_dialogue(path: Path) -> list[str]:
    lines = clean_lines(path)
    errors: list[str] = []
    expected = "المستخدم:"
    for number, line in enumerate(lines, start=1):
        if not line.startswith(expected):
            errors.append(
                f"{path}:{number}: expected a user turn beginning with 'المستخدم:'"
            )
        if number < len(lines):
            answer = lines[number]
            if not answer.startswith("Jon2:"):
                errors.append(
                    f"{path}:{number + 1}: expected an answer beginning with 'Jon2:'"
                )
    if len(lines) % 2:
        errors.append(f"{path}: dialogue has an unmatched final turn")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Jon2's local training text.")
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent / "training_data"),
        help="Folder containing UTF-8 .txt training files",
    )
    parser.add_argument(
        "--minimum-chars",
        type=int,
        default=100_000,
        help="Reference size for a warning only; not a quality guarantee",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return failure if below the reference size or exact duplicate lines exist",
    )
    args = parser.parse_args()

    folder = Path(args.data)
    files = sorted(folder.rglob("*.txt"))
    if not files:
        print(f"ERROR: no .txt files found in {folder}", file=sys.stderr)
        return 2

    total_chars = 0
    all_lines: list[str] = []
    errors: list[str] = []
    for path in files:
        lines = clean_lines(path)
        count = sum(len(line) for line in lines)
        total_chars += count
        all_lines.extend(lines)
        print(f"{path}: {count:,} characters | {len(lines):,} non-empty lines")
        if path.name == "original_dialogue_ar.txt":
            errors.extend(audit_dialogue(path))

    normalized = [re.sub(r"\\s+", " ", line).casefold() for line in all_lines]
    duplicates = [line for line, count in Counter(normalized).items() if count > 1]
    print(f"TOTAL: {total_chars:,} characters across {len(files)} files")
    print(f"EXACT NORMALIZED DUPLICATE LINES: {len(duplicates)}")

    if total_chars < args.minimum_chars:
        print(
            f"WARNING: below the {args.minimum_chars:,}-character reference. "
            "This is not a training-quality threshold or a guarantee of capability."
        )
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if args.strict and (total_chars < args.minimum_chars or duplicates):
        print("STRICT AUDIT FAILED.", file=sys.stderr)
        return 1
    if errors:
        return 1
    print("AUDIT PASSED: structure is readable; rights still require human review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
