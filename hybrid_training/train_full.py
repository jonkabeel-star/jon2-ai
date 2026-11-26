"""Fail-closed full-parameter SFT trainer for Jon2's separate helper model.

Reads only local approved TXT/JSONL data and a local model directory.
Never downloads anything, never touches the original Jon2 checkpoint, and
requires CUDA for training. All helper-model parameters remain trainable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

import torch

ALLOWED_USES = {"research_training", "public_model", "commercial_model"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_txt_dialogue(text: str, source: str) -> list[list[dict[str, str]]]:
    """Parse explicitly labeled alternating Arabic/English user and Jon2 turns."""
    labels = {
        "المستخدم": "user", "user": "user",
        "jon2": "assistant", "assistant": "assistant",
    }
    conversations = []
    current = []
    active_role = None
    active_parts = []

    def flush_message():
        nonlocal active_role, active_parts, current, conversations
        if active_role is None:
            return
        body = "\n".join(active_parts).strip()
        if not body:
            raise ValueError(f"{source}: empty {active_role} message.")
        if active_role == "user" and current and current[-1]["role"] == "assistant":
            current.append({"role": "user", "content": body})
        elif active_role == "assistant" and current and current[-1]["role"] == "user":
            current.append({"role": "assistant", "content": body})
            conversations.append(current)
            current = []
        else:
            raise ValueError(f"{source}: dialogue must alternate user then assistant.")
        active_role, active_parts = None, []

    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            if active_role is not None:
                active_parts.append("")
            continue
        if ":" in stripped or "：" in stripped:
            separator = ":" if ":" in stripped else "："
            label, remainder = stripped.split(separator, 1)
            role = labels.get(label.strip().lower())
            if role:
                flush_message()
                active_role = role
                active_parts = [remainder.strip()] if remainder.strip() else []
                continue
        if active_role is None:
            raise ValueError(
                f"{source}:{line_no}: expected a speaker label such as 'المستخدم:' or 'Jon2:'."
            )
        active_parts.append(stripped)
    flush_message()
    if current:
        raise ValueError(f"{source}: file ends with an unanswered user turn.")
    if not conversations:
        raise ValueError(f"{source}: no labeled dialogue pairs found.")
    return conversations


def parse_jsonl(text: str, source: str) -> list[list[dict[str, str]]]:
    conversations = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{line_no}: invalid JSON: {exc.msg}") from exc
        messages = record.get("messages") if isinstance(record, dict) else None
        if not isinstance(messages, list) or len(messages) < 2:
            raise ValueError(f"{source}:{line_no}: expected a messages array.")
        clean = []
        previous_role = None
        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError(f"{source}:{line_no}: invalid message object.")
            role, body = msg.get("role"), msg.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(body, str) or not body.strip():
                raise ValueError(f"{source}:{line_no}: invalid role/content.")
            if role == "system" and clean:
                raise ValueError(f"{source}:{line_no}: system message must be first.")
            if role == previous_role and role != "system":
                raise ValueError(f"{source}:{line_no}: consecutive {role} messages.")
            clean.append({"role": role, "content": body.strip()})
            previous_role = role
        if not any(m["role"] == "user" for m in clean) or clean[-1]["role"] != "assistant":
            raise ValueError(f"{source}:{line_no}: conversation must include user and end with assistant.")
        conversations.append(clean)
    return conversations


def validate_manifest(data_dir: Path, manifest_path: Path, intended_use: str):
    if intended_use not in ALLOWED_USES:
        raise ValueError(f"Unsupported intended use: {intended_use}")
    root = data_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
    if not manifest_path.is_file():
        raise PermissionError(f"Private approval manifest not found: {manifest_path}")

    files = sorted(
        path for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".jsonl"}
    )
    if not files:
        raise FileNotFoundError("No TXT/JSONL training sources found.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("approved_sources") if isinstance(manifest, dict) else None
    if not isinstance(records, list):
        raise PermissionError("Manifest must contain an approved_sources list.")

    approvals: dict[str, dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            raise PermissionError("Every approval needs a relative file path.")
        name = item["file"]
        rel = PurePosixPath(name)
        if (not name or rel.is_absolute() or rel.as_posix() != name or "\\" in name
                or any(part in ("", ".", "..") for part in rel.parts)):
            raise PermissionError(f"Unsafe approval path: {name!r}")
        if name in approvals:
            raise PermissionError(f"Duplicate approval: {name}")
        approvals[name] = item

    loaded = []
    actual_names = set()
    for path in files:
        if not path.resolve().is_relative_to(root):
            raise PermissionError(f"Source escapes data directory: {path}")
        name = path.relative_to(data_dir).as_posix()
        actual_names.add(name)
        raw = path.read_bytes()
        decoded = raw.decode("utf-8", errors="strict")
        approval = approvals.get(name)
        if approval is None:
            raise PermissionError(f"Training blocked: {name} has no exact-file approval.")
        if approval.get("status") != "APPROVED":
            raise PermissionError(f"Training blocked: {name} is not APPROVED.")
        if approval.get("sha256") != sha256_bytes(raw):
            raise PermissionError(f"Training blocked: {name} SHA-256 changed after approval.")
        if type(approval.get("character_count")) is not int or approval["character_count"] != len(decoded):
            raise PermissionError(f"Training blocked: {name} character count mismatch.")
        for field in ("reviewer", "review_date", "rights_basis"):
            if not isinstance(approval.get(field), str) or not approval[field].strip():
                raise PermissionError(f"Training blocked: {name} is missing {field}.")
        if approval.get("intended_use") != intended_use:
            raise PermissionError(
                f"Training blocked: {name} approval is for {approval.get('intended_use')!r}, "
                f"not {intended_use!r}."
            )
        parsed = parse_jsonl(decoded, name) if path.suffix.lower() == ".jsonl" else parse_txt_dialogue(decoded, name)
        loaded.extend((path, conversation) for conversation in parsed)

    if actual_names != set(approvals):
        raise PermissionError(
            f"Manifest mismatch. Missing={sorted(actual_names - set(approvals))}; "
            f"stale={sorted(set(approvals) - actual_names)}"
        )
    if not loaded:
        raise ValueError("No valid conversations were found.")
    return loaded


def normalized_conversation(messages):
    return json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def split_conversations(items, validation_fraction: float, seed: int):
    deduped = {}
    for item in items:
        key = hashlib.sha256(normalized_conversation(item[1]).encode("utf-8")).hexdigest()
        deduped.setdefault(key, item)
    ordered = sorted(
        deduped.items(),
        key=lambda pair: hashlib.sha256(f"{seed}:{pair[0]}".encode()).hexdigest(),
    )
    if len(ordered) < 3:
        raise ValueError("At least 3 unique conversations are required for train/validation.")
    validation_count = max(1, round(len(ordered) * validation_fraction))
    validation_count = min(validation_count, len(ordered) - 1)
    validation_keys = {key for key, _ in ordered[:validation_count]}
    train, validation = [], []
    for key, item in deduped.items():
        (validation if key in validation_keys else train).append(item)
    return train, validation, len(items) - len(deduped)


def build_turn_examples(conversations, tokenizer, max_length: int):
    examples, skipped_long = [], 0
    for _, messages in conversations:
        for index, message in enumerate(messages):
            if message["role"] != "assistant":
                continue
            prefix = messages[:index]
            if not prefix or not any(m["role"] == "user" for m in prefix):
                continue
            prompt_ids = tokenizer.apply_chat_template(
                prefix, tokenize=True, add_generation_prompt=True
            )
            full_ids = tokenizer.apply_chat_template(
                messages[:index + 1], tokenize=True, add_generation_prompt=False
            )
            if full_ids[:len(prompt_ids)] != prompt_ids:
                raise RuntimeError("Chat-template prefix mismatch; refusing unsafe label masking.")
            if len(full_ids) > max_length:
                skipped_long += 1
                continue
            if len(full_ids) <= len(prompt_ids):
                continue
            labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
            examples.append({
                "input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": labels,
            })
    return examples, skipped_long


class SimpleCausalCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features):
        max_len = max(len(row["input_ids"]) for row in features)
        pad_id = self.tokenizer.pad_token_id
        if pad_id is None:
            raise ValueError("Tokenizer has no pad token.")
        input_ids, masks, labels = [], [], []
        for row in features:
            pad = max_len - len(row["input_ids"])
            input_ids.append(row["input_ids"] + [pad_id] * pad)
            masks.append(row["attention_mask"] + [0] * pad)
            labels.append(row["labels"] + [-100] * pad)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(masks, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Full fine-tuning for Jon2's separate open-weight helper model.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--approval-manifest", required=True, type=Path)
    parser.add_argument("--intended-use", choices=sorted(ALLOWED_USES), default="research_training")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/jon2-helper-full-ft"))
    parser.add_argument("--validation-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=16)
    parser.add_argument("--precision", choices=("bf16", "fp16", "fp32"), default="bf16")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    if not 0.05 <= args.validation_fraction <= 0.30:
        raise ValueError("validation-fraction must be between 0.05 and 0.30.")
    if args.max_length < 128 or args.batch_size < 1 or args.gradient_accumulation < 1:
        raise ValueError("Invalid sequence/batch/gradient-accumulation setting.")

    conversations = validate_manifest(args.data_dir, args.approval_manifest, args.intended_use)
    train_rows, validation_rows, duplicate_count = split_conversations(
        conversations, args.validation_fraction, args.seed
    )
    print(json.dumps({
        "status": "preflight_passed",
        "source_files": len({str(path) for path, _ in conversations}),
        "unique_conversations": len(train_rows) + len(validation_rows),
        "train_conversations": len(train_rows),
        "validation_conversations": len(validation_rows),
        "exact_duplicates_removed": duplicate_count,
        "intended_use": args.intended_use,
        "full_fine_tuning": True,
        "lora": False,
        "original_jon2_checkpoint_touched": False,
        "gpu_training_started": False,
    }, ensure_ascii=False, indent=2))
    if args.preflight_only:
        return 0

    if args.model_dir is None or not args.model_dir.is_dir():
        raise FileNotFoundError("--model-dir must point to an already-downloaded local model directory.")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not detected. Training is blocked; no CPU/iPhone fallback.")
    if args.precision == "bf16" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("GPU does not support BF16; choose precision only after hardware review.")

    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.model_dir), local_files_only=True, trust_remote_code=False
    )
    if tokenizer.pad_token_id is None:
        if tokenizer.eos_token_id is None:
            raise ValueError("Tokenizer has neither pad token nor EOS token.")
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        str(args.model_dir),
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype={"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[args.precision],
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    if trainable != total:
        raise RuntimeError(f"Full fine-tuning guard failed: trainable={trainable}, total={total}.")

    train_examples, train_skipped = build_turn_examples(train_rows, tokenizer, args.max_length)
    eval_examples, eval_skipped = build_turn_examples(validation_rows, tokenizer, args.max_length)
    if len(train_examples) < 2 or not eval_examples:
        raise ValueError(f"Insufficient tokenized examples: train={len(train_examples)}, eval={len(eval_examples)}.")

    class TokenDataset(torch.utils.data.Dataset):
        def __init__(self, rows):
            self.rows = rows
        def __len__(self):
            return len(self.rows)
        def __getitem__(self, index):
            return self.rows[index]

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.gradient_accumulation,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=args.precision == "bf16",
        fp16=args.precision == "fp16",
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
        seed=args.seed,
        data_seed=args.seed,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=TokenDataset(train_examples),
        eval_dataset=TokenDataset(eval_examples),
        data_collator=SimpleCausalCollator(tokenizer),
        processing_class=tokenizer,
    )
    print(json.dumps({
        "status": "training_starting",
        "trainable_parameters": trainable,
        "total_parameters": total,
        "train_examples": len(train_examples),
        "validation_examples": len(eval_examples),
        "overlength_train_turns_skipped": train_skipped,
        "overlength_validation_turns_skipped": eval_skipped,
        "precision": args.precision,
        "full_fine_tuning": True,
    }, ensure_ascii=False, indent=2))
    trainer.train()
    final_dir = args.output_dir / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    metadata = {
        "model_source": str(args.model_dir),
        "intended_use": args.intended_use,
        "seed": args.seed,
        "max_length": args.max_length,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "precision": args.precision,
        "full_fine_tuning": True,
        "lora": False,
        "trainable_parameters": trainable,
        "total_parameters": total,
        "training_conversations": len(train_rows),
        "validation_conversations": len(validation_rows),
        "train_examples": len(train_examples),
        "validation_examples": len(eval_examples),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "jon2_training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Training finished. Candidate only; independent evaluation and human review remain mandatory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
