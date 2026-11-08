"""Fail-closed, dependency-free approval gate for Jon2 training data."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def validate_source_approvals(
    data_dir: Path, manifest_path: Path, *, include_jsonl: bool = False
) -> None:
    """Require exact-file approval for every selected TXT and optional JSONL source."""
    data_dir = Path(data_dir)
    root = data_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")

    files = {}
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix != ".txt" and not (include_jsonl and suffix == ".jsonl"):
            continue
        if not path.resolve().is_relative_to(root):
            raise PermissionError(f"Training text resolves outside data directory: {path}")
        relative_name = path.relative_to(data_dir).as_posix()
        raw = path.read_bytes()
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Training source is not valid UTF-8: {relative_name}") from exc
        if suffix == ".jsonl":
            for line_number, line in enumerate(decoded.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL source {relative_name}:{line_number}: {exc.msg}"
                    ) from exc
                messages = record.get("messages") if isinstance(record, dict) else None
                if not isinstance(messages, list) or not messages:
                    raise ValueError(
                        f"{relative_name}:{line_number} must contain a non-empty messages list."
                    )
                has_user = False
                has_assistant = False
                for message in messages:
                    if not isinstance(message, dict):
                        raise ValueError(
                            f"{relative_name}:{line_number} contains an invalid message object."
                        )
                    role = message.get("role")
                    content = message.get("content")
                    if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                        raise ValueError(
                            f"{relative_name}:{line_number} messages require user/assistant "
                            "roles and non-empty string content."
                        )
                    has_user = has_user or role == "user"
                    has_assistant = has_assistant or role == "assistant"
                if not has_user or not has_assistant:
                    raise ValueError(
                        f"{relative_name}:{line_number} needs both user and assistant turns."
                    )
        files[relative_name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "character_count": len(decoded),
        }

    if not files:
        raise FileNotFoundError(f"No .txt training files found in {data_dir}.")
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
                or relative.as_posix() != name
                or any(part in ("", ".", "..") for part in relative.parts)
                or "\\" in name):
            raise ValueError(f"Unsafe or non-normalized source path: {name!r}")
        if name in approvals:
            raise ValueError(f"Duplicate approval record for {name}.")
        approvals[name] = record

    missing = sorted(set(files) - set(approvals))
    unexpected = sorted(set(approvals) - set(files))
    if missing or unexpected:
        raise PermissionError(
            f"Training blocked. Missing approvals: {missing or 'none'}; "
            f"records without matching text files: {unexpected or 'none'}."
        )

    allowed_uses = {"research_training", "public_model", "commercial_model"}
    for name in sorted(files):
        record = approvals[name]
        expected_hash = files[name]["sha256"]
        supplied_hash = record.get("sha256")
        if not isinstance(supplied_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", supplied_hash):
            raise ValueError(f"Training source {name} requires a lowercase SHA-256 approval fingerprint.")
        if supplied_hash != expected_hash:
            raise PermissionError(f"Training blocked: {name} changed after its source approval was recorded.")
        if type(record.get("character_count")) is not int or record["character_count"] != files[name]["character_count"]:
            raise PermissionError(f"Training blocked: {name} character count does not match the approved file.")
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
