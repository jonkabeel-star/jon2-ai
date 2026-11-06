"""Build a local training corpus only from hash-pinned, rights-approved sources.

This module never downloads data. It refuses symlinks/path traversal, validates
the existing Jon2 rights manifest, verifies each source SHA-256, and writes
private JSONL outputs outside the repository by default.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .rights_gate import load_approved_sources


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Every approved source needs a local_path.")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("Source path cannot be absolute or traverse parent directories.")
    unresolved = root / relative_path
    cursor = root
    for part in relative_path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Training source path cannot contain symlinks.")
    candidate = unresolved.resolve(strict=True)
    resolved_root = root.resolve(strict=True)
    if candidate == resolved_root or resolved_root not in candidate.parents:
        raise ValueError("Source path must remain inside the declared private data root.")
    if not candidate.is_file():
        raise ValueError("Training source must be a regular file.")
    if candidate.suffix.lower() not in {".txt", ".jsonl"}:
        raise ValueError("Only UTF-8 .txt and .jsonl source files are supported.")
    return candidate


def _read_documents(path: Path) -> Iterable[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".txt":
        for paragraph in text.splitlines():
            paragraph = paragraph.strip()
            if paragraph:
                yield paragraph
        return
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path.name}:{line_number}") from exc
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError(f"JSONL record {line_number} must contain a string 'text' field.")
        value = item["text"].strip()
        if value:
            yield value


def build_corpus(manifest_path: str | Path, data_root: str | Path,
                 output_dir: str | Path) -> dict:
    """Verify approved source bytes and build a deterministic private document corpus."""
    manifest_path = Path(manifest_path).resolve(strict=True)
    root = Path(data_root).resolve(strict=True)
    destination = Path(output_dir).resolve()
    if destination == root or root in destination.parents:
        raise ValueError("Output directory must be separate from the source data root.")
    repository_root = next(
        (parent for parent in manifest_path.parents if (parent / ".git").exists()),
        None,
    )
    protected_roots = [manifest_path.parent]
    if repository_root is not None:
        protected_roots.append(repository_root)
    if any(destination == protected or protected in destination.parents for protected in protected_roots):
        raise ValueError("Private corpus output must not be written inside the Git repository.")

    sources = load_approved_sources(manifest_path)
    train_rows, validation_rows = [], []
    source_summaries = []
    global_seen_hashes = set()
    for source in sources:
        split = source.get("split")
        if split not in {"train", "validation"}:
            raise ValueError(f"Source {source.get('dataset_id')} must declare split='train' or split='validation'.")
        path = _safe_source_path(root, source.get("local_path"))
        actual_hash = sha256_file(path)
        if actual_hash != source["content_hash_sha256"]:
            raise ValueError(f"SHA-256 mismatch for approved source {source['dataset_id']}.")
        target = train_rows if split == "train" else validation_rows
        count_before = len(target)
        for text in _read_documents(path):
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if text_hash in global_seen_hashes:
                continue
            global_seen_hashes.add(text_hash)
            target.append({
                "text": text,
                "source_id": source["dataset_id"],
                "source_sha256": actual_hash,
            })
        source_summaries.append({
            "dataset_id": source["dataset_id"],
            "split": split,
            "sha256": actual_hash,
            "documents": len(target) - count_before,
        })

    if not train_rows or not validation_rows:
        raise ValueError("At least one approved source assigned to each of train and validation is required.")

    destination.mkdir(parents=True, exist_ok=True)
    train_path = destination / "train.jsonl"
    validation_path = destination / "validation.jsonl"
    _atomic_jsonl(train_path, train_rows)
    _atomic_jsonl(validation_path, validation_rows)

    return {
        "documents": len(train_rows) + len(validation_rows),
        "train_documents": len(train_rows),
        "validation_documents": len(validation_rows),
        "sources": source_summaries,
        "train_sha256": sha256_file(train_path),
        "validation_sha256": sha256_file(validation_path),
        "output_dir": str(destination),
        "downloaded_data": False,
        "rights_verified": True,
    }


def _atomic_jsonl(path: Path, rows: list[dict]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build a rights-verified private Jon2 corpus.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    report = build_corpus(args.manifest, args.data_root, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
