"""Download and normalize the ShawarmaChats dialogues config into private JSONL.

Only the official train split enters the training folder. The official test split
is written to a separate evaluation folder and is never passed to the trainer.
This script requires explicit research-only and ShareAlike review acknowledgements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

DATASET_ID = "Kamyar-zeinalipour/arabic_multi_dialect_dialogue"
DATASET_CARD = "https://huggingface.co/datasets/Kamyar-zeinalipour/arabic_multi_dialect_dialogue"
LICENSE = "CC-BY-SA-4.0"


def _parse_dialogue(value):
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        value = json.loads(text)
    if isinstance(value, dict):
        value = value.get("dialogue")
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("dialogue must be a list with at least two turns")
    messages = []
    expected = "A"
    for turn in value:
        if not isinstance(turn, dict):
            raise ValueError("dialogue turn must be an object")
        speaker = turn.get("speaker")
        content = turn.get("text")
        if speaker != expected:
            raise ValueError("dialogue speakers must alternate A/B starting with A")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("dialogue turn text must be non-empty")
        messages.append({
            "role": "user" if speaker == "A" else "assistant",
            "content": content.strip(),
        })
        expected = "B" if expected == "A" else "A"
    if len(messages) % 2:
        raise ValueError("dialogue must contain a complete A/B turn pair")
    return messages


def _write_jsonl(path: Path, records: list[dict]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)
    raw = path.read_bytes()
    return {
        "file": path.name,
        "records": len(records),
        "characters": sum(len(message["content"]) for row in records for message in row["messages"]),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize ShawarmaChats into private Jon2 dialogue JSONL.")
    parser.add_argument("--revision", required=True, help="Immutable Hugging Face commit SHA; never use a moving branch.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Private persistent-volume output directory outside the repository.")
    parser.add_argument("--dialects", default="msa,egyptian", help="Comma-separated subset of msa,egyptian,maghrebi.")
    parser.add_argument("--confirm-private-research-only", action="store_true")
    parser.add_argument("--confirm-sharealike-review", action="store_true")
    args = parser.parse_args()

    if not args.confirm_private_research_only or not args.confirm_sharealike_review:
        parser.error("Explicitly confirm private research-only use and review CC BY-SA 4.0 ShareAlike terms.")
    if len(args.revision) < 20 or any(ch not in "0123456789abcdef" for ch in args.revision.lower()):
        parser.error("--revision must be an immutable hexadecimal commit SHA.")
    allowed = {"msa", "egyptian", "maghrebi"}
    dialects = {part.strip().lower() for part in args.dialects.split(",") if part.strip()}
    if not dialects or not dialects.issubset(allowed):
        parser.error("--dialects may contain only msa,egyptian,maghrebi.")
    output = args.output_dir.resolve()
    repo_root = Path(__file__).resolve().parents[2]
    if output == repo_root or repo_root in output.parents:
        parser.error("Output must be outside the Git repository on private persistent storage.")

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install ai_engine/datasets/requirements-ingest.txt first.") from exc

    dataset = load_dataset(DATASET_ID, "dialogues", revision=args.revision)
    if "train" not in dataset or "test" not in dataset:
        raise SystemExit("Expected official train and test splits; refusing to invent a split.")

    def convert(split_name: str) -> tuple[list[dict], Counter]:
        result = []
        counts = Counter()
        for index, row in enumerate(dataset[split_name]):
            dialect = str(row.get("dialect", "")).strip().lower()
            if dialect not in dialects:
                continue
            messages = _parse_dialogue(row.get("dialogue"))
            source_id = str(row.get("id") or f"{split_name}-{index}")
            result.append({
                "messages": messages,
                "source": {
                    "dataset": DATASET_ID,
                    "revision": args.revision,
                    "source_split": split_name,
                    "source_id": source_id,
                    "page_id": row.get("page_id"),
                    "source_url": row.get("url"),
                    "category": row.get("category"),
                    "dialect": dialect,
                    "license": LICENSE,
                    "attribution": "ShawarmaChats dataset authors; underlying Arabic Wikipedia sources are linked per record",
                },
            })
            counts[dialect] += 1
        return result, counts

    train_records, train_counts = convert("train")
    test_records, test_counts = convert("test")
    if not train_records or not test_records:
        raise SystemExit("Selected dialects produced an empty official train or test split; no output accepted.")

    train_path = output / "training" / "shawarmachats_train.jsonl"
    test_path = output / "evaluation-only" / "shawarmachats_official_test.jsonl"
    train_info = _write_jsonl(train_path, train_records)
    test_info = _write_jsonl(test_path, test_records)
    manifest = {
        "format": "jon2-shawarmachats-intake-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": DATASET_ID,
        "dataset_card": DATASET_CARD,
        "revision": args.revision,
        "license": LICENSE,
        "use_scope": "private_non_commercial_research_only",
        "selected_dialects": sorted(dialects),
        "training": {**train_info, "dialect_counts": dict(train_counts)},
        "official_test_evaluation_only": {**test_info, "dialect_counts": dict(test_counts)},
        "policy": {
            "official_test_copied_to_training": False,
            "source_approval_manifest_created": False,
            "training_started": False,
            "human_review_required": True,
            "sharealike_review_acknowledged_by_operator": True,
        },
    }
    manifest_path = output / "intake-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("INTAKE COMPLETE: private files written; no source approvals or training were created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
