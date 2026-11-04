"""Fail-closed, dependency-free approval gate for Jon2 training data."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath


def validate_source_approvals(data_dir: Path, manifest_path: Path) -> None:
    """Require one explicit human approval for every training .txt source."""
    data_dir = Path(data_dir)
    root = data_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")

    files = set()
    for path in data_dir.rglob("*.txt"):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            raise PermissionError(f"Training text resolves outside data directory: {path}")
        files.add(path.relative_to(data_dir).as_posix())

    if not files:
        raise FileNotFoundError(f"No training .txt files found in {data_dir}.")
    if not manifest_path.is_file():
        raise PermissionError(
            f"Training blocked: approval manifest not found at {manifest_path}. "
            "Review each source and create source_approvals.json privately."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid source approval manifest: {exc}") from exc

    records = manifest.get("approved_sources") if isinstance(manifest, dict) else None
    if not isinstance(records, list):
        raise ValueError("Manifest must contain an 'approved_sources' list.")

    approvals = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("file"), str):
            raise ValueError("Every approval record must contain a relative 'file' path.")
        name = record["file"]
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute()
                or any(part in ("", ".", "..") for part in relative.parts)
                or "\\\\" in name):
            raise ValueError(f"Unsafe or non-normalized source path: {name!r}")
        if name in approvals:
            raise ValueError(f"Duplicate approval record for {name}.")
        approvals[name] = record

    missing = sorted(files - set(approvals))
    unexpected = sorted(set(approvals) - files)
    if missing or unexpected:
        raise PermissionError(
            f"Training blocked. Missing approvals: {missing or 'none'}; "
            f"records without matching text files: {unexpected or 'none'}."
        )

    allowed_uses = {"research_training", "public_model", "commercial_model"}
    for name in sorted(files):
        record = approvals[name]
        if record.get("status") != "APPROVED":
            raise PermissionError(f"Training blocked: {name} is not APPROVED.")
        for field in ("reviewer", "review_date", "rights_basis"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise PermissionError(f"Training blocked: {name} lacks {field}.")
        if record.get("intended_use") not in allowed_uses:
            raise PermissionError(
                f"Training blocked: {name} has no valid intended_use approval."
            )
    print(f"Source approval gate: PASS ({len(files)} text files explicitly approved).")
