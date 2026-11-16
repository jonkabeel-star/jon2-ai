"""Build a private, review-gated dataset from Jon2-original authored conversations.

Input JSONL stays outside GitHub. Every record must explicitly identify its
author, rights basis, category, and fixed train/eval assignment. This script
never approves data and never starts training.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

INPUT = Path(os.environ.get(
    "JON2_ORIGINAL_SOURCE",
    "/kaggle/working/jon2_original_source.jsonl",
))
OUTPUT = Path(os.environ.get(
    "JON2_ORIGINAL_OUTPUT",
    "/kaggle/working/jon2_original_dataset",
))
ALLOWED_SPLITS = {"train", "eval"}
ALLOWED_ROLES = {"user", "assistant"}
MIN_TRAIN = 100
MIN_EVAL = 30


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_messages(messages: list[dict]) -> str:
    return json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_record(item: object, line_no: int) -> dict:
    if not isinstance(item, dict):
        raise ValueError(f"Line {line_no}: each JSONL row must be an object.")
    required = {"id", "category", "split", "author", "rights_basis", "messages"}
    missing = required - set(item)
    if missing:
        raise ValueError(f"Line {line_no}: missing fields: {sorted(missing)}")
    for key in ("id", "category", "author", "rights_basis"):
        if not isinstance(item[key], str) or not item[key].strip():
            raise ValueError(f"Line {line_no}: {key} must be a non-empty string.")
    if item["split"] not in ALLOWED_SPLITS:
        raise ValueError(f"Line {line_no}: split must be train or eval.")
    if not isinstance(item["messages"], list) or len(item["messages"]) < 2:
        raise ValueError(f"Line {line_no}: messages must contain at least two turns.")
    messages = item["messages"]
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict) or set(msg) != {"role", "content"}:
            raise ValueError(f"Line {line_no}: message {i} must contain only role/content.")
        if msg["role"] not in ALLOWED_ROLES:
            raise ValueError(f"Line {line_no}: unsupported role at message {i}.")
        if not isinstance(msg["content"], str) or not msg["content"].strip():
            raise ValueError(f"Line {line_no}: empty/non-text message at turn {i}.")
        if i and msg["role"] == messages[i - 1]["role"]:
            raise ValueError(f"Line {line_no}: roles must alternate.")
    if messages[0]["role"] != "user" or messages[-1]["role"] != "assistant":
        raise ValueError(f"Line {line_no}: conversation must start user and end assistant.")
    if item["author"].lower() in {"unknown", "internet", "youtube"}:
        raise ValueError(f"Line {line_no}: author must identify the actual author.")
    if "original" not in item["rights_basis"].lower():
        raise ValueError(
            f"Line {line_no}: rights_basis must explicitly state the original-authorship basis."
        )
    return {
        "id": item["id"].strip(),
        "category": item["category"].strip(),
        "split": item["split"],
        "author": item["author"].strip(),
        "rights_basis": item["rights_basis"].strip(),
        "messages": messages,
    }


def main() -> None:
    if not INPUT.is_file():
        raise FileNotFoundError(
            f"Missing {INPUT}. Create a private JSONL source file first; "
            "do not put private training data in the public repository."
        )
    if OUTPUT.exists():
        raise FileExistsError(
            f"{OUTPUT} already exists. Existing data will not be overwritten. "
            "Set JON2_ORIGINAL_OUTPUT to a new empty directory."
        )

    rows = []
    with INPUT.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                rows.append(validate_record(json.loads(line), line_no))
    if not rows:
        raise ValueError("Input dataset is empty.")

    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record IDs detected.")
    fingerprints = [hashlib.sha256(canonical_messages(r["messages"]).encode("utf-8")).hexdigest() for r in rows]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("Duplicate conversations detected.")

    train = [r for r in rows if r["split"] == "train"]
    evaluation = [r for r in rows if r["split"] == "eval"]
    if not train or not evaluation:
        raise ValueError("Both train and eval splits are required.")
    train_hashes = {hashlib.sha256(canonical_messages(r["messages"]).encode("utf-8")).hexdigest() for r in train}
    eval_hashes = {hashlib.sha256(canonical_messages(r["messages"]).encode("utf-8")).hexdigest() for r in evaluation}
    if train_hashes & eval_hashes:
        raise ValueError("Train/eval leakage detected.")

    OUTPUT.mkdir(parents=True)
    summaries = {}
    for split, split_rows in (("train", train), ("eval", evaluation)):
        folder = OUTPUT / split
        folder.mkdir()
        data_file = folder / f"{split}.jsonl"
        with data_file.open("w", encoding="utf-8") as f:
            for row in split_rows:
                f.write(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n")
        manifest = {
            "dataset": "Jon2 Original Egyptian Dataset",
            "dataset_version": "0.1.0",
            "split": split,
            "source_file_sha256": sha256(INPUT),
            "output_file": data_file.name,
            "output_sha256": sha256(data_file),
            "records": len(split_rows),
            "characters": sum(len(m["content"]) for r in split_rows for m in r["messages"]),
            "categories": dict(Counter(r["category"] for r in split_rows)),
            "license_basis": "Original project-authored content; rights review still required",
            "approval_status": "PENDING_HUMAN_REVIEW",
            "commercial_use_approved": False,
            "reviewer": "",
            "review_date": "",
            "rights_confirmation": "",
            "note": "No third-party dataset rights are inherited; verify every record's authorship and permissions.",
        }
        (folder / "source_approvals.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summaries[split] = manifest

    report = {
        "dataset": "Jon2 Original Egyptian Dataset",
        "version": "0.1.0",
        "input_sha256": sha256(INPUT),
        "train": summaries["train"],
        "eval": summaries["eval"],
        "minimum_counts_met": len(train) >= MIN_TRAIN and len(evaluation) >= MIN_EVAL,
        "status": "PENDING_HUMAN_REVIEW",
        "training_started": False,
    }
    (OUTPUT / "preparation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "train_records": len(train),
        "eval_records": len(evaluation),
        "train_categories": summaries["train"]["categories"],
        "eval_categories": summaries["eval"]["categories"],
        "train_sha256": summaries["train"]["output_sha256"],
        "eval_sha256": summaries["eval"]["output_sha256"],
        "minimum_counts_met": report["minimum_counts_met"],
        "status": "PENDING_HUMAN_REVIEW",
        "training_started": False,
        "output": str(OUTPUT),
    }, ensure_ascii=False, indent=2))
    print("STOP: Review every record and confirm rights before changing any approval status.")


if __name__ == "__main__":
    main()
