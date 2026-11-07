"""Lightweight loader for approved Jon2 Arabic training sources.

Kept free of PyTorch so corpus parsing and validation can run in small CI jobs.
"""
from __future__ import annotations

import json
from pathlib import Path

def read_corpus(folder: Path) -> str:
    """Read approved plain-text and JSONL dialogue sources into training text.

    JSONL records must contain a messages array with user/assistant turns.
    Each conversation becomes its own blank-line-delimited block so the
    training/validation splitter can keep complete conversations together.
    """
    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".jsonl"}
    )
    if not files:
        raise FileNotFoundError(f"No .txt or .jsonl training files found in {folder}.")

    parts = []
    for path in files:
        raw_text = path.read_text(encoding="utf-8", errors="strict")
        if path.suffix.lower() == ".txt":
            lines = raw_text.splitlines()
            # Ignore metadata/comment lines while keeping the authored text.
            useful = [line for line in lines if not line.lstrip().startswith("#")]
            text = "\n".join(useful).strip()
            if text:
                parts.append(text)
            continue

        for line_number, line in enumerate(raw_text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL record in {path}:{line_number}: {exc.msg}"
                ) from exc
            messages = record.get("messages") if isinstance(record, dict) else None
            if not isinstance(messages, list) or not messages:
                raise ValueError(
                    f"JSONL record in {path}:{line_number} must contain a non-empty messages list."
                )
            turns = []
            has_assistant = False
            for message in messages:
                if not isinstance(message, dict):
                    raise ValueError(
                        f"Invalid message object in {path}:{line_number}."
                    )
                role = message.get("role")
                content = message.get("content")
                if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                    raise ValueError(
                        f"Messages in {path}:{line_number} require role user/assistant "
                        "and non-empty string content."
                    )
                label = "المستخدم" if role == "user" else "Jon2"
                has_assistant = has_assistant or role == "assistant"
                turns.append(f"{label}: {content.strip()}")
            if not has_assistant:
                raise ValueError(
                    f"JSONL conversation in {path}:{line_number} has no assistant response."
                )
            parts.append("\n".join(turns))

    corpus = "\n\n".join(parts).strip()
    if len(corpus) < 1000:
        raise ValueError(
            f"Corpus has only {len(corpus)} characters. Add more original or "
            "properly licensed training text before training."
        )
    return corpus

