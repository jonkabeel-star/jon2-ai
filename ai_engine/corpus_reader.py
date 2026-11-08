"""Lightweight loader for approved Jon2 Arabic training sources.

Kept free of PyTorch so corpus parsing and validation can run in small CI jobs.
"""
from __future__ import annotations

import json
from pathlib import Path

def read_corpus(folder: Path) -> str:
    """Read approved plain-text sources only. Structured JSONL dialogue is deliberately excluded.

    JSONL records must contain a messages array with user/assistant turns.
    Each conversation becomes its own blank-line-delimited block so the
    training/validation splitter can keep complete conversations together.
    """
    files = sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() == ".txt"
    )
    if not files:
        raise FileNotFoundError(f"No .txt training files found in {folder}.")

    parts = []
    for path in files:
        raw_text = path.read_text(encoding="utf-8", errors="strict")
        lines = raw_text.splitlines()
        # Ignore metadata/comment lines while keeping the authored text.
        useful = [line for line in lines if not line.lstrip().startswith("#")]
        text = "\n".join(useful).strip()
        if text:
            parts.append(text)

    corpus = "\n\n".join(parts).strip()
    if len(corpus) < 1000:
        raise ValueError(
            f"Corpus has only {len(corpus)} characters. Add more original or "
            "properly licensed training text before training."
        )
    return corpus

