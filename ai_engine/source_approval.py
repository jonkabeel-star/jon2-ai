"""Fail-closed, source-by-source approval gate for Jon2 training data.

This module uses only the Python standard library so its policy checks can be
tested without installing PyTorch or starting a training run.
"""
from __future__ import annotations

import json
from pathlib import Path


def validate_source_approvals(data_dir: Path, manifest_path: Path) -> None:
    """Require an explicit human approval record for every .txt source file."""
    data_dir = Path(data_dir)
    manifest_path = Path(manifest_path)
    files = {
        path.relative_to(data_dir).as_posix()
        for path in data_dir.rglob("*.txt")
        if path.is_file()
    }
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

    approvals: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("file"), str):
            raise ValueError("Every approval record must contain a relative 'file' path.")
        name = record["file"]
        candidate = Path(name)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Unsafe source path in approval manifest: {name}")
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
