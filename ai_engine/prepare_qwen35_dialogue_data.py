"""Prepare a private Qwen3.5 LoRA corpus from exact-file-approved Jon2 Arabic text.

This tool never downloads data. It only reads .txt files covered by a private
source_approvals.json manifest, creates deterministic conversation-level
train/validation JSONL, and emits a PENDING owner-review manifest. Training
must remain blocked until the owner reviews the transformed files and changes
every pending record to APPROVED with reviewer/date/rights_basis.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, random, re
from pathlib import Path
from source_approval import validate_source_approvals


PREFIX = re.compile(r"^(المستخدم|المساعد|Jon2|User|Assistant)\s*:\s*(.*)$", re.I)
ROLE = {
    "المستخدم": "user", "user": "user",
    "المساعد": "assistant", "jon2": "assistant", "assistant": "assistant",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = re.sub(r"[أإآ]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def parse_file(path: Path) -> list[dict]:
    conversations = []
    current = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = PREFIX.match(line.strip())
        if match:
            role = ROLE[match.group(1).casefold()]
            content = match.group(2).strip()
            if not content:
                continue
            if current and current[-1]["role"] == role:
                # A repeated speaker marker is malformed; do not silently join it.
                raise ValueError(f"{path.name}:{line_no}: repeated {role} turn.")
            current.append({"role": role, "content": content})
        elif not line.strip():
            if current:
                conversations.append(current)
                current = []
        elif line.lstrip().startswith("#"):
            continue
        else:
            raise ValueError(f"{path.name}:{line_no}: unrecognized non-empty line.")
    if current:
        conversations.append(current)

    valid = []
    for index, messages in enumerate(conversations, 1):
        if messages[0]["role"] != "user" or messages[-1]["role"] != "assistant":
            raise ValueError(f"{path.name}: conversation {index} must start user and end assistant.")
        if any(messages[i]["role"] == messages[i-1]["role"] for i in range(1, len(messages))):
            raise ValueError(f"{path.name}: conversation {index} has non-alternating roles.")
        valid.append({"messages": messages, "source_file": path.name})
    return valid


def fingerprint(row: dict) -> str:
    payload = json.dumps(row["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--source-approval-manifest", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--validation-fraction", type=float, default=0.12)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if not 0.05 <= args.validation_fraction <= 0.25:
        raise ValueError("validation-fraction must be between 0.05 and 0.25.")
    validate_source_approvals(args.source_dir, args.source_approval_manifest, include_jsonl=False)
    approval = json.loads(args.source_approval_manifest.read_text(encoding="utf-8"))
    records = {x["file"]: x for x in approval["approved_sources"]}
    source_files = sorted(args.source_dir.rglob("*.txt"))
    if not source_files:
        raise FileNotFoundError("No approved UTF-8 .txt sources found.")
    all_rows = []
    for path in source_files:
        rel = path.relative_to(args.source_dir).as_posix()
        if records[rel].get("intended_use") != "research_training":
            raise PermissionError(f"{rel} is not approved for research_training.")
        if path.name == "original_seed_ar.txt":
            print(f"{rel}: approved prose seed; excluded from supervised dialogue conversion.")
            continue
        if path.name not in {
            "original_dialogue_ar.txt",
            "original_dialogue_ar_batch_01.txt",
            "original_dialogue_ar_batch_02.txt",
            "original_dialogue_ar_batch_03.txt",
            "original_dialogue_ar_batch_04.txt",
        }:
            raise PermissionError(f"Unexpected approved text source for this dialogue converter: {rel}")
        parsed = parse_file(path)
        all_rows.extend(parsed)
        print(f"{rel}: {len(parsed)} conversations | sha256={sha256_bytes(path.read_bytes())}")
    # Exact duplicate and normalized user-prompt duplicate checks.
    seen = set()
    seen_prompts = set()
    unique = []
    for row in all_rows:
        fp = fingerprint(row)
        first_user = next(m["content"] for m in row["messages"] if m["role"] == "user")
        prompt_fp = hashlib.sha256(normalize(first_user).encode("utf-8")).hexdigest()
        if fp in seen:
            continue
        if prompt_fp in seen_prompts:
            raise ValueError("Near-duplicate first user prompt detected; manually deduplicate before splitting.")
        seen.add(fp)
        seen_prompts.add(prompt_fp)
        unique.append(row)
    if len(unique) < 130:
        raise ValueError(f"Only {len(unique)} unique conversations. Need >=130 for >=100 train and >=30 validation.")
    rng = random.Random(args.seed)
    indices = list(range(len(unique)))
    rng.shuffle(indices)
    eval_count = max(30, round(len(unique) * args.validation_fraction))
    if len(unique) - eval_count < 100:
        raise ValueError("Not enough unique conversations for 100 train and 30 validation examples.")
    eval_ids = set(indices[:eval_count])
    train_rows = [unique[i] for i in range(len(unique)) if i not in eval_ids]
    eval_rows = [unique[i] for i in range(len(unique)) if i in eval_ids]
    # Verify no exact message-sequence overlap.
    if {fingerprint(x) for x in train_rows} & {fingerprint(x) for x in eval_rows}:
        raise RuntimeError("Leakage detected after split.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    def write_jsonl(path: Path, rows: list[dict]):
        payload = "".join(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n" for row in rows)
        path.write_text(payload, encoding="utf-8")
        raw = path.read_bytes()
        return {
            "file": path.name, "sha256": sha256_bytes(raw),
            "character_count": len(payload), "status": "PENDING_OWNER_REVIEW",
            "reviewer": "", "review_date": "", "rights_basis": "",
            "intended_use": "research_training",
        }
    train_dir = args.output_dir / "train"
    eval_dir = args.output_dir / "validation"
    train_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    train_record = write_jsonl(train_dir / "train.jsonl", train_rows)
    eval_record = write_jsonl(eval_dir / "validation.jsonl", eval_rows)
    common = {
        "format": "jon2-derived-qwen35-corpus-approval-v1",
        "note": "PENDING. Human owner must review exact bytes and quality before setting status APPROVED.",
        "source_manifest_sha256": sha256_bytes(args.source_approval_manifest.read_bytes()),
        "seed": args.seed, "validation_fraction": args.validation_fraction,
        "approved_sources_used": sorted(records),
    }
    for folder, record, count in ((train_dir, train_record, len(train_rows)), (eval_dir, eval_record, len(eval_rows))):
        pending = {**common, "conversation_count": count, "approved_sources": [record]}
        (folder / "source_approvals.pending.json").write_text(
            json.dumps(pending, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
        )
    with (args.output_dir / "owner_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "source_file", "messages_json", "review_decision", "review_notes"])
        writer.writeheader()
        for split, rows in (("train", train_rows), ("validation", eval_rows)):
            for row in rows:
                writer.writerow({
                    "split": split, "source_file": row["source_file"],
                    "messages_json": json.dumps(row["messages"], ensure_ascii=False),
                    "review_decision": "", "review_notes": "",
                })
    report = {
        "total_source_conversations": len(all_rows),
        "unique_conversations": len(unique),
        "train_conversations": len(train_rows),
        "validation_conversations": len(eval_rows),
        "leakage_exact_match": False,
        "training_started": False,
        "approval_status": "PENDING_OWNER_REVIEW",
    }
    (args.output_dir / "preparation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("STOP: review owner_review.csv and exact JSONL bytes; do not train until approval manifest is completed.")


if __name__ == "__main__":
    main()
