"""Deterministic byte-level BPE tokenizer trained only on the supplied corpus.

The tokenizer keeps UTF-8 byte fallback, so unseen Arabic letters, Latin text,
punctuation, and emoji remain representable. It is a tokenizer, not a pretrained
language model and does not add linguistic knowledge by itself.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

# Keep word, whitespace, and punctuation boundaries during BPE training.
_PRETOKENIZE = re.compile(r"\\s+|[\\w]+|[^\\w\\s]", flags=re.UNICODE)


class ByteBPETokenizer:
    """Small dependency-free byte-level BPE implementation."""

    def __init__(self, merges: list[tuple[int, int]] | None = None):
        self.merges = list(merges or [])
        self._merge_ranks = {pair: rank for rank, pair in enumerate(self.merges)}
        self._byte_cache: dict[int, bytes] = {i: bytes([i]) for i in range(256)}

    @property
    def vocab_size(self) -> int:
        return 256 + len(self.merges)

    @classmethod
    def train(
        cls,
        text: str,
        vocab_size: int = 1000,
        min_frequency: int = 2,
    ) -> "ByteBPETokenizer":
        if not text:
            raise ValueError("Cannot train a tokenizer on empty text.")
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256 for byte fallback.")
        if min_frequency < 1:
            raise ValueError("min_frequency must be positive.")

        sequences = [
            list(piece.encode("utf-8"))
            for piece in _PRETOKENIZE.findall(text)
            if piece
        ]
        merges: list[tuple[int, int]] = []

        while 256 + len(merges) < vocab_size:
            pair_counts: Counter[tuple[int, int]] = Counter()
            for sequence in sequences:
                pair_counts.update(zip(sequence, sequence[1:]))
            if not pair_counts:
                break
            best_pair, frequency = min(
                pair_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if frequency < min_frequency:
                break

            new_id = 256 + len(merges)
            merges.append(best_pair)
            updated = []
            for sequence in sequences:
                result = []
                index = 0
                while index < len(sequence):
                    if (
                        index + 1 < len(sequence)
                        and (sequence[index], sequence[index + 1]) == best_pair
                    ):
                        result.append(new_id)
                        index += 2
                    else:
                        result.append(sequence[index])
                        index += 1
                updated.append(result)
            sequences = updated

        return cls(merges)

    def _encode_piece(self, piece: str) -> list[int]:
        ids = list(piece.encode("utf-8"))
        for rank, pair in enumerate(self.merges):
            merged_id = 256 + rank
            result = []
            index = 0
            while index < len(ids):
                if (
                    index + 1 < len(ids)
                    and (ids[index], ids[index + 1]) == pair
                ):
                    result.append(merged_id)
                    index += 2
                else:
                    result.append(ids[index])
                    index += 1
            ids = result
        return ids

    def encode(self, text: str) -> list[int]:
        result: list[int] = []
        for piece in _PRETOKENIZE.findall(text):
            result.extend(self._encode_piece(piece))
        return result

    def _token_bytes(self, token_id: int, active: set[int] | None = None) -> bytes:
        if token_id in self._byte_cache:
            return self._byte_cache[token_id]
        if token_id < 256 or token_id >= self.vocab_size:
            raise ValueError(f"Invalid token id: {token_id}")
        active = active or set()
        if token_id in active:
            raise ValueError("Tokenizer merge table contains a cycle.")
        active.add(token_id)
        left, right = self.merges[token_id - 256]
        value = self._token_bytes(left, active) + self._token_bytes(right, active)
        active.remove(token_id)
        self._byte_cache[token_id] = value
        return value

    def decode(self, ids: Iterable[int]) -> str:
        raw = b"".join(self._token_bytes(int(token_id)) for token_id in ids)
        return raw.decode("utf-8", errors="replace")

    def to_dict(self) -> dict:
        return {
            "format": "jon2-byte-bpe-v1",
            "base_vocab_size": 256,
            "merges": [list(pair) for pair in self.merges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ByteBPETokenizer":
        if data.get("format") != "jon2-byte-bpe-v1":
            raise ValueError("Unsupported tokenizer format.")
        if data.get("base_vocab_size") != 256:
            raise ValueError("Tokenizer base vocabulary must contain 256 bytes.")
        merges = data.get("merges")
        if not isinstance(merges, list):
            raise ValueError("Tokenizer merges must be a list.")
        parsed = []
        for expected_id, pair in enumerate(merges, start=256):
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or any(not isinstance(value, int) for value in pair)
                or any(value < 0 or value >= expected_id for value in pair)
            ):
                raise ValueError(f"Invalid BPE merge definition at token {expected_id}.")
            parsed.append((pair[0], pair[1]))
        return cls(parsed)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "ByteBPETokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
