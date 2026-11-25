"""Deterministic three-way split for complete JSONL dialogue conversations.

This module is a data-preparation utility, not an approval mechanism. Callers must
run the exact-file rights/approval gate before using any returned partition for
training. Conversations sharing any normalized message are kept in one group so
question/answer text cannot leak across train, validation, and test.
"""
from __future__ import annotations

import hashlib
import json
import random
import unicodedata
from collections import defaultdict


def normalize_message(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = "".join(
        char for char in value
        if unicodedata.category(char) != "Mn" and char != "\u0640"
    )
    return " ".join(value.split())


def _fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_message(text).encode("utf-8")).hexdigest()


def _record_group_fingerprints(record: dict, index: int) -> list[str]:
    """Return namespaced fingerprints for source/document grouping metadata."""
    if not isinstance(record, dict):
        raise ValueError(f"Conversation {index}: record must be an object.")
    source = record.get("source")
    if source is not None and not isinstance(source, dict):
        raise ValueError(f"Conversation {index}: source metadata must be an object.")
    source = source or {}
    dataset = source.get("dataset", "")
    if not isinstance(dataset, str):
        raise ValueError(f"Conversation {index}: source dataset identifier must be text.")
    fingerprints = []
    for container_name, container in (("record", record), ("source", source)):
        for field in ("conversation_id", "document_id", "group_id", "source_id", "page_id"):
            value = container.get(field)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
                raise ValueError(f"Conversation {index}: invalid {container_name}.{field}.")
            namespace = dataset if container_name == "source" else ""
            key = f"{namespace}\0{container_name}.{field}\0{normalize_message(str(value))}"
            fingerprints.append(hashlib.sha256(key.encode("utf-8")).hexdigest())
    return fingerprints


def validate_conversation(record: dict, index: int) -> list[str]:
    messages = record.get("messages") if isinstance(record, dict) else None
    if not isinstance(messages, list) or not messages or len(messages) % 2:
        raise ValueError(f"Conversation {index}: messages must be a non-empty even-length list.")
    contents = []
    for position, message in enumerate(messages):
        expected_role = "user" if position % 2 == 0 else "assistant"
        if not isinstance(message, dict) or message.get("role") != expected_role:
            raise ValueError(f"Conversation {index}: expected {expected_role} at message {position}.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Conversation {index}: message {position} is empty.")
        contents.append(content)
    return contents


def split_dialogue_records(
    records: list[dict],
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 42,
) -> dict[str, list[dict]]:
    """Split whole conversations; shared normalized message text forms one group.

    The split fails closed when fewer than three independent groups exist.
    Fractions refer to conversation counts approximately; linked duplicate
    conversations remain together even when this makes ratios less exact.
    """
    if not isinstance(records, list) or len(records) < 3:
        raise ValueError("At least three conversation records are required.")
    if not 0 < validation_fraction < 0.5 or not 0 < test_fraction < 0.5:
        raise ValueError("validation_fraction and test_fraction must be between 0 and 0.5.")
    if validation_fraction + test_fraction >= 0.8:
        raise ValueError("Validation and test fractions must leave at least 20% for training.")

    message_owners: dict[str, list[int]] = defaultdict(list)
    group_owners: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        for content in validate_conversation(record, index):
            message_owners[_fingerprint(content)].append(index)
        for fingerprint in _record_group_fingerprints(record, index):
            group_owners[fingerprint].append(index)

    parent = list(range(len(records)))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    for owners in (*message_owners.values(), *group_owners.values()):
        for owner in owners[1:]:
            union(owners[0], owner)

    grouped: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        grouped[find(index)].append(index)
    groups = list(grouped.values())
    if len(groups) < 3:
        raise ValueError(
            "At least three independent conversation groups are required for train/validation/test."
        )

    rng = random.Random(seed)
    rng.shuffle(groups)
    groups.sort(key=len, reverse=True)

    total = len(records)
    targets = {
        "train": total * (1.0 - validation_fraction - test_fraction),
        "validation": total * validation_fraction,
        "test": total * test_fraction,
    }
    result: dict[str, list[dict]] = {name: [] for name in targets}
    counts = {name: 0 for name in targets}

    # Seed each partition with a distinct independent group.
    names = ["train", "validation", "test"]
    for name, group in zip(names, groups[:3]):
        result[name].extend(records[index] for index in group)
        counts[name] += len(group)

    for group in groups[3:]:
        # Prefer the partition with the largest remaining proportional deficit.
        name = max(
            names,
            key=lambda candidate: (
                targets[candidate] - counts[candidate],
                targets[candidate],
            ),
        )
        result[name].extend(records[index] for index in group)
        counts[name] += len(group)

    # A final hard assertion protects against future algorithm changes.
    owners: dict[str, set[str]] = {}
    for name, partition in result.items():
        fingerprints = set()
        for index, record in enumerate(partition):
            for content in validate_conversation(record, f"{name}:{index}"):
                fingerprints.add(_fingerprint(content))
        owners[name] = fingerprints
    if (
        owners["train"] & owners["validation"]
        or owners["train"] & owners["test"]
        or owners["validation"] & owners["test"]
    ):
        raise RuntimeError("Normalized message leakage detected across partitions.")

    return result


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc.msg}") from exc
    return records


def write_jsonl_partitions(partitions, output_dir):
    """Write audit partitions to a caller-selected directory; never modifies input."""
    from pathlib import Path

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for name, records in partitions.items():
        path = destination / f"{name}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")

def prepare_approved_dialogue_splits(
    data_dir,
    approval_manifest,
    output_dir,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 42,
) -> dict:
    """Validate exact source approvals, split all approved JSONL conversations,
    and write isolated train/validation/test files plus a content-hash manifest.

    The output directory must be outside the source tree. This routine never
    approves data, edits source files, trains a model, or loads checkpoints.
    """
    import hashlib
    from pathlib import Path

    from source_approval import validate_source_approvals

    source_root = Path(data_dir).resolve()
    destination = Path(output_dir).resolve()
    manifest_path = Path(approval_manifest).resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"Dialogue source directory not found: {source_root}")
    if destination == source_root or source_root in destination.parents:
        raise ValueError("Dialogue split output must be outside the source data directory.")

    # This gate intentionally checks every selected TXT/JSONL source in the
    # folder. An unapproved file blocks the operation instead of being skipped.
    validate_source_approvals(
        source_root, manifest_path, include_jsonl=True
    )
    source_files = sorted(source_root.rglob("*.jsonl"))
    if not source_files:
        raise FileNotFoundError("No approved JSONL dialogue files were found.")

    records = []
    source_inventory = []
    for path in source_files:
        raw = path.read_bytes()
        decoded = raw.decode("utf-8", errors="strict")
        source_records = load_jsonl(path)
        if not source_records:
            raise ValueError(f"Approved dialogue source is empty: {path.relative_to(source_root)}")
        records.extend(source_records)
        source_inventory.append({
            "file": path.relative_to(source_root).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "conversation_count": len(source_records),
        })

    partitions = split_dialogue_records(
        records,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        seed=seed,
    )
    write_jsonl_partitions(partitions, destination)

    output_inventory = {}
    for name in ("train", "validation", "test"):
        output_path = destination / f"{name}.jsonl"
        raw = output_path.read_bytes()
        output_inventory[name] = {
            "conversation_count": len(partitions[name]),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "file": output_path.name,
        }

    report = {
        "schema_version": 1,
        "algorithm": "conversation_message_overlap_union_find_v1",
        "seed": seed,
        "validation_fraction": validation_fraction,
        "test_fraction": test_fraction,
        "source_files": source_inventory,
        "total_conversations": len(records),
        "partitions": output_inventory,
        "test_partition_policy": "held_out_only_never_train_or_select_checkpoint",
        "approval_manifest_validated": True,
        "model_training_started": False,
        "source_files_modified": False,
    }
    report_path = destination / "split_manifest.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
