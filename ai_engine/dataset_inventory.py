"""Build a privacy-conscious inventory of Jon2 training text.

The report contains file metadata and approval-gate status only; it never copies
training text into the report. Token counts use a temporary BPE tokenizer trained
on the selected corpus and are estimates for that exact corpus/configuration.

Optional source-provenance fields are reported when present in the approval
manifest. Missing provenance is surfaced for human review, but this descriptive
audit never grants rights or changes the existing training approval decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from source_approval import validate_source_approvals
from tokenizer import ByteBPETokenizer


PROVENANCE_FIELDS = (
    "source_url",
    "publisher",
    "language",
    "dialect",
    "license",
    "attribution_requirements",
    "retrieval_date",
)


def _manifest_records(manifest_path: Path) -> dict[str, dict]:
    """Read optional provenance metadata without replacing the strict approval gate."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    records = manifest.get("approved_sources") if isinstance(manifest, dict) else None
    if not isinstance(records, list):
        return {}
    result = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        name = record.get("file")
        if isinstance(name, str) and name not in result:
            result[name] = record
    return result


def _optional_text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def build_inventory(
    data_dir: Path,
    approval_manifest: Path,
    vocab_size: int = 512,
) -> dict:
    data_dir = Path(data_dir)
    root = data_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")
    if vocab_size < 256:
        raise ValueError("vocab_size must be at least 256.")

    approval_records = _manifest_records(Path(approval_manifest))
    entries = []
    texts = []
    total_bytes = total_chars = total_lines = total_nonempty_lines = 0

    for path in sorted(data_dir.rglob("*.txt")):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            raise PermissionError(f"Training text resolves outside data directory: {path}")
        raw = path.read_bytes()
        decoded = raw.decode("utf-8", errors="strict")
        relative = path.relative_to(data_dir).as_posix()
        lines = decoded.splitlines()
        nonempty = sum(1 for line in lines if line.strip())
        checksum = hashlib.sha256(raw).hexdigest()
        approval_record = approval_records.get(relative, {})
        provenance = {
            field: _optional_text(approval_record.get(field))
            for field in PROVENANCE_FIELDS
        }
        missing_fields = [
            field for field in PROVENANCE_FIELDS if provenance[field] is None
        ]
        entries.append({
            "file": relative,
            "sha256": checksum,
            "bytes": len(raw),
            "characters": len(decoded),
            "lines": len(lines),
            "nonempty_lines": nonempty,
            "provenance": {
                **provenance,
                "checksum_sha256": checksum,
                "approval_recorded_checksum_sha256": _optional_text(
                    approval_record.get("sha256")
                ),
                "status": "COMPLETE" if not missing_fields else "INCOMPLETE",
                "missing_fields": missing_fields,
            },
            "rights_review": {
                "status": _optional_text(approval_record.get("status")),
                "reviewer": _optional_text(approval_record.get("reviewer")),
                "review_date": _optional_text(approval_record.get("review_date")),
                "rights_basis": _optional_text(approval_record.get("rights_basis")),
                "intended_use": _optional_text(approval_record.get("intended_use")),
            },
        })
        texts.append(decoded)
        total_bytes += len(raw)
        total_chars += len(decoded)
        total_lines += len(lines)
        total_nonempty_lines += nonempty

    if not entries:
        raise FileNotFoundError(f"No training .txt files found in {data_dir}.")

    combined = "\n".join(texts)
    tokenizer = ByteBPETokenizer.train(combined, vocab_size=vocab_size)
    for entry, source_text in zip(entries, texts):
        entry["tokens"] = len(tokenizer.encode(source_text))

    try:
        validate_source_approvals(data_dir, Path(approval_manifest))
        approval = {"status": "APPROVED", "source_count": len(entries), "reason": None}
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        approval = {
            "status": "BLOCKED",
            "source_count": len(entries),
            "reason": str(exc),
        }

    missing_field_counts = {
        field: sum(
            1 for entry in entries
            if entry["provenance"][field] is None
        )
        for field in PROVENANCE_FIELDS
    }
    complete_count = sum(
        1 for entry in entries if entry["provenance"]["status"] == "COMPLETE"
    )

    return {
        "schema_version": 2,
        "tool": "Jon2 AI dataset inventory",
        "tokenizer": {
            "type": "temporary_byte_bpe",
            "vocab_size_target": vocab_size,
            "vocab_size_actual": tokenizer.vocab_size,
            "note": "Token counts are corpus-specific inventory metrics, not model-quality scores.",
        },
        "totals": {
            "files": len(entries),
            "bytes": total_bytes,
            "characters": total_chars,
            "lines": total_lines,
            "nonempty_lines": total_nonempty_lines,
            "tokens": sum(item["tokens"] for item in entries),
        },
        "approval_gate": approval,
        "provenance_audit": {
            "fields_checked": list(PROVENANCE_FIELDS),
            "files_with_complete_metadata": complete_count,
            "files_with_incomplete_metadata": len(entries) - complete_count,
            "missing_field_counts": missing_field_counts,
            "note": (
                "Informational metadata audit only. Missing fields do not grant or "
                "deny reuse rights and do not change the exact-file approval gate. "
                "The checksum is computed from the current source bytes."
            ),
        },
        "files": entries,
        "training_permitted": approval["status"] == "APPROVED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory Jon2 UTF-8 training text without exposing its contents."
    )
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parent / "training_data"),
    )
    parser.add_argument(
        "--approval-manifest",
        default=str(Path(__file__).resolve().parent / "training_data" / "source_approvals.json"),
    )
    parser.add_argument("--vocab-size", type=int, default=512)
    parser.add_argument("--output", help="Optional JSON report path; defaults to stdout.")
    args = parser.parse_args()

    try:
        report = build_inventory(
            Path(args.data), Path(args.approval_manifest), vocab_size=args.vocab_size
        )
    except (OSError, UnicodeError, ValueError, PermissionError) as exc:
        print(f"INVENTORY FAILED: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        print(f"Inventory written to {destination}")
    else:
        print(rendered, end="")
    print(
        f"Inventory: {report['totals']['files']} files, "
        f"{report['totals']['characters']:,} characters, "
        f"{report['totals']['tokens']:,} tokens; "
        f"approval={report['approval_gate']['status']}; "
        f"provenance_complete={report['provenance_audit']['files_with_complete_metadata']}/"
        f"{report['totals']['files']}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
