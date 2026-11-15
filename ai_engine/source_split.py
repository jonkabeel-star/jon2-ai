"""Leakage-resistant deterministic splitting of approved corpus sources."""
from __future__ import annotations

import hashlib
import math
import random
import re
import unicodedata


def _normalized_fingerprint(text: str) -> str:
    value = unicodedata.normalize("NFC", text)
    value = value.replace("\u0640", "")
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = " ".join(value.casefold().split())
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_corpus_sources(sources, validation_fraction: float, seed: int):
    """Split complete approved files; never split paragraphs from one file across sets.

    sources is an iterable of (stable_source_id, text). Every file is one group.
    Exact normalized paragraph overlap between partitions is a hard error.
    """
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("validation_fraction must be between 0.05 and 0.4.")
    normalized = []
    seen_ids = set()
    for source_id, text in sources:
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("Every corpus source needs a stable non-empty source ID.")
        if source_id in seen_ids:
            raise ValueError(f"Duplicate corpus source ID: {source_id}")
        seen_ids.add(source_id)
        if not isinstance(text, str) or not text.strip():
            continue
        normalized.append((source_id, text.strip()))
    if len(normalized) < 2:
        raise ValueError(
            "At least two independently approved source files are required "
            "for a source-isolated train/validation split."
        )

    indices = list(range(len(normalized)))
    random.Random(seed).shuffle(indices)
    validation_count = max(1, math.ceil(len(indices) * validation_fraction))
    if validation_count >= len(indices):
        raise ValueError("Not enough independent source files for train/validation.")
    validation_indices = set(indices[:validation_count])

    train_sources = [item for i, item in enumerate(normalized) if i not in validation_indices]
    validation_sources = [item for i, item in enumerate(normalized) if i in validation_indices]

    def paragraph_fingerprints(items):
        fingerprints = set()
        for _, text in items:
            for paragraph in re.split(r"\n\s*\n", text):
                paragraph = paragraph.strip()
                if paragraph:
                    fingerprints.add(_normalized_fingerprint(paragraph))
        return fingerprints

    overlap = paragraph_fingerprints(train_sources) & paragraph_fingerprints(validation_sources)
    if overlap:
        raise ValueError(
            f"Normalized duplicate content crosses train/validation ({len(overlap)} "
            "matching paragraph fingerprints). Reconcile source lineage or duplicates "
            "before training; do not silently move examples between splits."
        )

    train_text = "\n\n".join(text for _, text in train_sources)
    validation_text = "\n\n".join(text for _, text in validation_sources)
    return train_text, validation_text
