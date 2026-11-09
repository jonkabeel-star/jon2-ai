"""Read project-owned Arabic training text and optionally structured dialogue.

JSONL dialogue loading is opt-in. The production trainer keeps it disabled until
each exact JSONL file has a matching source-approval record. Corpus-size policy
belongs to the trainer, not this reader, so small fixtures can test parsing.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_dialogue_jsonl(path: Path) -> list[str]:
    conversations: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSONL record in {path.name}:{line_number}: {exc.msg}"
            ) from exc
        messages = record.get("messages") if isinstance(record, dict) else None
        if not isinstance(messages, list) or not messages:
            raise ValueError(
                f"Invalid JSONL record in {path.name}:{line_number}: messages must be a non-empty list."
            )
        turns = []
        has_user = False
        has_assistant = False
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError(
                    f"Invalid JSONL record in {path.name}:{line_number}: each message must be an object."
                )
            role = message.get("role")
            text = message.get("content")
            if role not in {"user", "assistant"} or not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"Invalid JSONL record in {path.name}:{line_number}: use non-empty user/assistant messages."
                )
            has_user = has_user or role == "user"
            has_assistant = has_assistant or role == "assistant"
            label = "المستخدم" if role == "user" else "Jon2"
            turns.append(f"{label}: {text.strip()}")
        if not has_user or not has_assistant:
            raise ValueError(
                f"Invalid JSONL record in {path.name}:{line_number}: each conversation needs user and assistant turns."
            )
        conversations.append("\n".join(turns))
    return conversations


def read_corpus(folder: Path, include_jsonl: bool = False) -> str:
    """Read UTF-8 .txt sources; optionally format JSONL messages as complete conversations.

    JSONL is opt-in so unapproved dialogue files cannot silently enter training.
    Each conversation is kept in its own blank-line-delimited block for splitting.
    Minimum corpus-size checks are enforced by the training entry point.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {folder}.")
    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and (
            path.suffix.lower() == ".txt"
            or (include_jsonl and path.suffix.lower() == ".jsonl")
        )
    )
    if not files:
        expected = ".txt or approved .jsonl" if include_jsonl else ".txt"
        raise FileNotFoundError(f"No {expected} training files found in {folder}.")

    parts: list[str] = []
    for path in files:
        if path.suffix.lower() == ".jsonl":
            parts.extend(_read_dialogue_jsonl(path))
            continue
        raw_text = path.read_text(encoding="utf-8", errors="strict")
        lines = raw_text.splitlines()
        useful = [line for line in lines if not line.lstrip().startswith("#")]
        text = "\n".join(useful).strip()
        if text:
            parts.append(text)

    # Remove exact duplicate blocks without reordering the original examples.
    unique_parts = list(dict.fromkeys(part.strip() for part in parts if part.strip()))
    return "\n\n".join(unique_parts).strip()
