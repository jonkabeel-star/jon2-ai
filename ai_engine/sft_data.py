"""Conversation-level SFT preparation for the original Jon2 Byte-BPE model.

Only assistant response tokens contribute to the loss. User messages and role
markers remain visible as context but receive IGNORE_INDEX labels.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

try:
    from .tokenizer import ByteBPETokenizer
    from .source_approval import validate_source_approvals
except ImportError:  # Running as: python ai_engine/sft_data.py
    from tokenizer import ByteBPETokenizer
    from source_approval import validate_source_approvals

IGNORE_INDEX = -100
USER_MARKER = "### المستخدم:\n"
ASSISTANT_MARKER = "### Jon2:\n"
TURN_END = "\n"


def encode_conversation(
    messages: list[dict[str, Any]],
    tokenizer: ByteBPETokenizer,
    *,
    max_length: int,
) -> dict[str, list[int]]:
    """Encode one strictly alternating user/assistant conversation.

    No truncation is performed: dropping a prompt or cutting an answer could
    silently change the training target. Oversized records fail closed.
    """
    if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length < 2:
        raise ValueError("max_length must be an integer greater than or equal to 2.")
    if not isinstance(messages, list) or len(messages) < 2 or len(messages) % 2:
        raise ValueError("A conversation must contain complete user/assistant pairs.")

    input_ids: list[int] = []
    labels: list[int] = []
    supervised_tokens = 0

    for index, message in enumerate(messages):
        expected_role = "user" if index % 2 == 0 else "assistant"
        if not isinstance(message, dict) or message.get("role") != expected_role:
            raise ValueError(
                f"Conversation messages must alternate user/assistant; "
                f"message {index + 1} must be {expected_role!r}."
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Message {index + 1} must contain non-empty text.")

        marker = USER_MARKER if expected_role == "user" else ASSISTANT_MARKER
        marker_ids = tokenizer.encode(marker)
        content_ids = tokenizer.encode(content.strip())
        end_ids = tokenizer.encode(TURN_END) if expected_role == "assistant" else tokenizer.encode(TURN_END)

        input_ids.extend(marker_ids)
        labels.extend([IGNORE_INDEX] * len(marker_ids))

        input_ids.extend(content_ids)
        if expected_role == "assistant":
            labels.extend(content_ids)
            supervised_tokens += len(content_ids)
        else:
            labels.extend([IGNORE_INDEX] * len(content_ids))

        input_ids.extend(end_ids)
        if expected_role == "assistant":
            labels.extend(end_ids)
            supervised_tokens += len(end_ids)
        else:
            labels.extend([IGNORE_INDEX] * len(end_ids))

    if supervised_tokens == 0:
        raise ValueError("Conversation contains no assistant target tokens.")
    if len(input_ids) > max_length:
        raise ValueError(
            f"Conversation encodes to {len(input_ids)} tokens, exceeding "
            f"max_length={max_length}; split it at a complete turn boundary."
        )
    if len(input_ids) != len(labels):
        raise AssertionError("input_ids and labels must have identical lengths.")
    if all(label == IGNORE_INDEX for label in labels):
        raise ValueError("Conversation has no supervised assistant tokens.")

    return {"input_ids": input_ids, "labels": labels}


def _read_jsonl_files(data_dir: Path) -> list[list[dict[str, str]]]:
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"SFT data directory not found: {data_dir}")
    text_files = sorted(data_dir.rglob("*.txt"))
    if text_files:
        raise ValueError(
            "SFT accepts JSONL conversations only. Use a dedicated directory "
            "without .txt files so ordinary language-model data cannot be mixed in."
        )
    files = sorted(data_dir.rglob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No .jsonl conversation files found in {data_dir}.")

    conversations: list[list[dict[str, str]]] = []
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL record in {path.name}:{line_number}: {exc.msg}"
                ) from exc
            messages = record.get("messages") if isinstance(record, dict) else None
            if not isinstance(messages, list):
                raise ValueError(
                    f"{path.name}:{line_number} must contain a messages array."
                )
            conversations.append(messages)
    if len(conversations) < 2:
        raise ValueError("At least two approved conversations are required for a train/validation split.")
    return conversations


def load_approved_sft_splits(
    data_dir: str | Path,
    approval_manifest: str | Path,
    tokenizer: ByteBPETokenizer,
    *,
    max_length: int,
    validation_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict[str, list[int]]], list[dict[str, list[int]]]]:
    """Validate exact-file approvals, encode conversations, then split by record."""
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("validation_fraction must be between 0.05 and 0.4.")
    data_dir = Path(data_dir)
    validate_source_approvals(
        data_dir, Path(approval_manifest), include_jsonl=True
    )
    conversations = _read_jsonl_files(data_dir)
    encoded = [
        encode_conversation(messages, tokenizer, max_length=max_length)
        for messages in conversations
    ]

    indices = list(range(len(encoded)))
    random.Random(seed).shuffle(indices)
    validation_count = max(1, round(len(indices) * validation_fraction))
    validation_indices = set(indices[:validation_count])
    train = [item for i, item in enumerate(encoded) if i not in validation_indices]
    validation = [item for i, item in enumerate(encoded) if i in validation_indices]
    if not train or not validation:
        raise ValueError("The conversation-level split must have non-empty train and validation sets.")
    return train, validation


class SFTConversationDataset(Dataset):
    def __init__(self, examples: list[dict[str, list[int]]]):
        if not examples:
            raise ValueError("SFT dataset cannot be empty.")
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.examples[index]


def collate_sft_batch(
    examples: list[dict[str, list[int]]],
    *,
    pad_token_id: int = 0,
) -> dict[str, torch.Tensor]:
    """Right-pad batches; padding labels are ignored by cross-entropy."""
    if not examples:
        raise ValueError("Cannot collate an empty batch.")
    width = max(len(item["input_ids"]) for item in examples)
    if width == 0:
        raise ValueError("SFT examples cannot be empty.")

    input_batch = []
    label_batch = []
    for item in examples:
        input_ids = item["input_ids"]
        labels = item["labels"]
        if len(input_ids) != len(labels) or not input_ids:
            raise ValueError("Every example needs matching, non-empty input_ids and labels.")
        padding = width - len(input_ids)
        input_batch.append(input_ids + [pad_token_id] * padding)
        label_batch.append(labels + [IGNORE_INDEX] * padding)

    return {
        "input_ids": torch.tensor(input_batch, dtype=torch.long),
        "labels": torch.tensor(label_batch, dtype=torch.long),
    }
