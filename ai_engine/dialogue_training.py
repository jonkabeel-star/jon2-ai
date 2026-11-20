"""Load integrity-checked train/validation partitions without exposing held-out test data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from dialogue_split import load_jsonl, normalize_message, validate_conversation
from source_approval import validate_source_approvals


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_relative_file(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name:
        raise ValueError(f"Unsafe split manifest path: {name!r}")
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or any(part in ("", ".", "..") for part in path.parts)
        or "\\" in name
    ):
        raise ValueError(f"Unsafe split manifest path: {name!r}")
    return path


def _format_training_text(records: list[dict], partition: str) -> str:
    blocks = []
    for index, record in enumerate(records):
        messages = validate_conversation(record, f"{partition}:{index}")
        turns = []
        for position, content in enumerate(messages):
            label = "المستخدم" if position % 2 == 0 else "Jon2"
            turns.append(f"{label}: {content.strip()}")
        blocks.append("\n".join(turns))
    return "\n\n".join(blocks)


def load_dialogue_training_partitions(
    split_dir: str | Path,
    data_dir: str | Path,
    approval_manifest: str | Path,
) -> tuple[str, str, dict]:
    """Return train and validation text; verify but never decode/use test JSONL.

    Every source must still match its private approval record and the exact
    source hashes recorded by the split manifest. Train/validation output hashes
    and counts are checked before they can reach the tokenizer or trainer.
    The test file is only read as bytes for integrity verification; its JSON
    records are never parsed, tokenized, sampled, or used for checkpoint choice.
    """
    source_root = Path(data_dir).resolve()
    split_root = Path(split_dir).resolve()
    if not source_root.is_dir() or not split_root.is_dir():
        raise FileNotFoundError("Both approved source and split directories must exist.")
    if split_root == source_root or source_root in split_root.parents:
        raise ValueError("Prepared split directory must be outside the source data directory.")

    manifest_path = split_root / "split_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("split_manifest.json is required.")
    manifest_raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid split manifest: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ValueError("Split manifest must be a JSON object.")
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported dialogue split manifest schema.")
    if manifest.get("algorithm") != "conversation_message_overlap_union_find_v1":
        raise ValueError("Unrecognized or unsafe conversation split algorithm.")
    if manifest.get("test_partition_policy") != "held_out_only_never_train_or_select_checkpoint":
        raise ValueError("Split manifest does not guarantee a held-out test partition.")

    # Revalidate exact source approvals and rights on every training invocation.
    validate_source_approvals(
        source_root, Path(approval_manifest), include_jsonl=True
    )
    source_entries = manifest.get("source_files")
    if not isinstance(source_entries, list) or not source_entries:
        raise ValueError("Split manifest must list its exact JSONL source files.")

    expected_sources = set()
    verified_sources = []
    for entry in source_entries:
        if not isinstance(entry, dict):
            raise ValueError("Malformed source inventory entry.")
        relative = _safe_relative_file(entry.get("file"))
        if relative.suffix.lower() != ".jsonl":
            raise ValueError("Three-way dialogue source inventory may contain JSONL only.")
        if relative.as_posix() in expected_sources:
            raise ValueError("Duplicate source path in split manifest.")
        expected_sources.add(relative.as_posix())
        path = (source_root / relative).resolve()
        if source_root not in path.parents or not path.is_file():
            raise PermissionError(f"Approved dialogue source is missing or outside data root: {relative}")
        raw = path.read_bytes()
        if _sha256(raw) != entry.get("sha256"):
            raise PermissionError(f"Dialogue source changed after splitting: {relative}")
        # Hash the complete approved source bytes without parsing source conversations.
        # This preserves the held-out partition as evaluation-only data.
        if type(entry.get("conversation_count")) is not int or entry["conversation_count"] < 1:
            raise ValueError(f"Invalid conversation count in source inventory: {relative}")
        verified_sources.append({
            "file": relative.as_posix(),
            "sha256": entry["sha256"],
            "conversation_count": entry["conversation_count"],
        })

    actual_sources = {
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*.jsonl") if path.is_file()
    }
    if actual_sources != expected_sources:
        raise PermissionError("JSONL source inventory changed after the three-way split was prepared.")

    partitions = manifest.get("partitions")
    if not isinstance(partitions, dict) or set(partitions) != {"train", "validation", "test"}:
        raise ValueError("Split manifest must contain exactly train, validation, and test partitions.")

    loaded = {}
    verified_partitions = {}
    for name in ("train", "validation", "test"):
        entry = partitions[name]
        if not isinstance(entry, dict):
            raise ValueError(f"Malformed {name} partition inventory.")
        expected_filename = f"{name}.jsonl"
        if entry.get("file") != expected_filename:
            raise ValueError(f"Unexpected {name} partition filename.")
        partition_path = split_root / expected_filename
        if not partition_path.is_file():
            raise FileNotFoundError(f"Missing {name} partition file.")
        raw = partition_path.read_bytes()
        if _sha256(raw) != entry.get("sha256"):
            raise PermissionError(f"{name} partition changed after split preparation.")
        verified_partitions[name] = {
            "file": expected_filename,
            "sha256": entry["sha256"],
            "conversation_count": entry.get("conversation_count"),
        }
        if name != "test":
            # Crucial: the held-out test JSONL is not parsed or passed to training.
            records = load_jsonl(partition_path)
            if len(records) != entry.get("conversation_count"):
                raise PermissionError(f"{name} partition count does not match its manifest.")
            if not records:
                raise ValueError(f"{name} partition is empty.")
            loaded[name] = records
        elif type(entry.get("conversation_count")) is not int or entry["conversation_count"] < 1:
            raise ValueError("Held-out test partition count is invalid.")

    train_messages = {
        hashlib.sha256(normalize_message(value).encode("utf-8")).hexdigest()
        for index, record in enumerate(loaded["train"])
        for value in validate_conversation(record, f"train:{index}")
    }
    validation_messages = {
        hashlib.sha256(normalize_message(value).encode("utf-8")).hexdigest()
        for index, record in enumerate(loaded["validation"])
        for value in validate_conversation(record, f"validation:{index}")
    }
    if train_messages & validation_messages:
        raise RuntimeError("Normalized message leakage detected between train and validation.")

    train_text = _format_training_text(loaded["train"], "train")
    validation_text = _format_training_text(loaded["validation"], "validation")
    metadata = {
        "algorithm": manifest["algorithm"],
        "seed": manifest.get("seed"),
        "split_manifest_sha256": _sha256(manifest_raw),
        "source_files": verified_sources,
        "partitions": verified_partitions,
        "test_partition_used_for_training": False,
        "test_partition_used_for_checkpoint_selection": False,
    }
    return train_text, validation_text, metadata
