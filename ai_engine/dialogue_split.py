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
    for index, record in enumerate(records):
        for content in validate_conversation(record, index):
            message_owners[_fingerprint(content)].append(index)

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

    for owners in message_owners.values():
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
