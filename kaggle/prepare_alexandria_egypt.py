"""Prepare a private Egyptian subset of UBC-NLP/Alexandria for review.

Important: Alexandria is CC BY-NC 4.0. This script is for private,
non-commercial research preparation only. It does not grant commercial rights,
does not approve sources, and does not make data production-ready.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

DATASET_ID = "UBC-NLP/alexandria"
DATASET_CONFIG = "EG"
SOURCE_URL = "https://huggingface.co/datasets/UBC-NLP/alexandria"
LICENSE = "CC BY-NC 4.0"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_conversation(row: dict) -> list[dict]:
    turns = row.get("dialectal_conversation")
    if not isinstance(turns, list):
        return []
    turns = sorted(
        [t for t in turns if isinstance(t, dict) and isinstance(t.get("text"), str)
         and t["text"].strip()],
        key=lambda t: int(t.get("turn_order", 0)),
    )
    # Create adjacent two-turn supervised exchanges. Do not assume the whole
    # dialogue alternates perfectly; reject same-speaker pairs and preserve
    # each original utterance exactly.
    examples = []
    for first, second in zip(turns, turns[1:]):
        speaker_a = str(first.get("speaker", "")).strip()
        speaker_b = str(second.get("speaker", "")).strip()
        if not speaker_a or not speaker_b or speaker_a == speaker_b:
            continue
        examples.append({
            "messages": [
                {"role": "user", "content": first["text"].strip()},
                {"role": "assistant", "content": second["text"].strip()},
            ]
        })
    return examples

def write_split(dataset, target: Path) -> tuple[int, int]:
    target.mkdir(parents=True, exist_ok=True)
    output = target / ("train.jsonl" if target.name == "train" else "eval.jsonl")
    seen = set()
    count = 0
    chars = 0
    with output.open("w", encoding="utf-8") as f:
        for row in dataset:
            item = convert_conversation(row)
            if item is None:
                continue
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
            chars += sum(len(m["content"]) for m in item["messages"])
    manifest = {
        "dataset": DATASET_ID,
        "config": DATASET_CONFIG,
        "split": target.name,
        "license": LICENSE,
        "source_url": SOURCE_URL,
        "attribution": "Alexandria dataset authors and contributors; cite ACL 2026 paper.",
        "intended_use": "research_training",
        "approval_status": "PENDING_HUMAN_REVIEW",
        "approved_sources": [{
            "file": output.name,
            "sha256": digest(output),
            "character_count": len(output.read_text(encoding="utf-8")),
            "status": "PENDING",
            "reviewer": "",
            "review_date": "",
            "rights_basis": "",
            "intended_use": "research_training",
        }],
    }
    (target / "source_approvals.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return count, chars


def main():
    from datasets import load_dataset

    root = Path("/tmp/jon2_alexandria_egypt")
    if root.exists():
        shutil.rmtree(root)
    print("Loading Egyptian subset from", DATASET_ID)
    print("License:", LICENSE, "| PRIVATE NON-COMMERCIAL RESEARCH ONLY")
    from datasets import get_dataset_split_names
    available_splits = get_dataset_split_names(DATASET_ID, config_name=DATASET_CONFIG)
    print("Available Egyptian splits:", available_splits)
    heldout_name = next((name for name in ("test", "validation", "dev") if name in available_splits), None)
    if "train" not in available_splits or heldout_name is None:
        raise RuntimeError(
            "Expected train plus a separate test/validation/dev split. "
            "Refusing to create a random split from training data."
        )
    train = load_dataset(DATASET_ID, name=DATASET_CONFIG, split="train")
    heldout = load_dataset(DATASET_ID, name=DATASET_CONFIG, split=heldout_name)
    train_count, train_chars = write_split(train, root / "train")
    eval_count, eval_chars = write_split(heldout, root / "eval")
    print("\nPREPARATION REPORT")
    print("Train conversations:", train_count, "| characters:", train_chars)
    print("Held-out test conversations:", eval_count, "| characters:", eval_chars)
    print("Train directory:", root / "train")
    print("Eval directory:", root / "eval")
    print("Train approval manifest:", root / "train" / "source_approvals.json")
    print("Eval approval manifest:", root / "eval" / "source_approvals.json")
    print("\nSTATUS: NOT APPROVED. Both manifests are deliberately PENDING.")
    print("Human review and license confirmation are required before training.")
    print("This Egyptian subset is domain/dialogue data, not a broad general-knowledge corpus.")
    if train_count < 100 or eval_count < 30:
        print("BLOCKED: fewer than 100 train or 30 held-out examples; do not train.")


if __name__ == "__main__":
    main()
