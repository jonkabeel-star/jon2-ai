"""Rights-gated Qwen2.5 Arabic LoRA fine-tuning for Jon2 AI.

Dry-run is the default. Real optimizer steps require --execute and CUDA.
This creates a separate PEFT adapter; it never overwrites Jon2's original checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

BASE_MODEL = "Qwen/Qwen3.5-2B"
BASE_MODEL_LICENSE = "Apache-2.0"
USER_LABELS = ("المستخدم:", "User:")
ASSISTANT_LABELS = ("Jon2:", "المساعد:", "Assistant:")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
EGYPT_MOBILE_RE = re.compile(r"(?<![A-Za-z0-9])(?:\+?20|0)?1[0125]\d{8}(?![A-Za-z0-9])")
SECRET_RE = re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{12,}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_approved_dialogue_files(data_dir: Path, manifest_path: Path) -> tuple[list[Path], dict[str, str]]:
    """Require exact SHA-256 + character-count approval for every TXT file."""
    data_dir = Path(data_dir)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    entries = manifest.get("approved_sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Approval manifest has no approved_sources entries.")

    approved: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "APPROVED":
            continue
        name = entry.get("file")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Approval manifest contains an unsafe file name.")
        if entry.get("intended_use") != "research_training":
            raise ValueError(f"{name}: intended_use must be research_training.")
        if not isinstance(entry.get("reviewer"), str) or not entry["reviewer"].strip():
            raise ValueError(f"{name}: reviewer is required.")
        if not isinstance(entry.get("rights_basis"), str) or not entry["rights_basis"].strip():
            raise ValueError(f"{name}: rights_basis is required.")
        if not isinstance(entry.get("review_date"), str) or not entry["review_date"].strip():
            raise ValueError(f"{name}: review_date is required.")
        if name in approved:
            raise ValueError(f"Duplicate approval entry for {name}.")
        approved[name] = entry

    files = sorted(data_dir.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files found in {data_dir}.")
    actual_names = {p.name for p in files}
    if actual_names != set(approved):
        missing = sorted(actual_names - set(approved))
        stale = sorted(set(approved) - actual_names)
        raise ValueError(f"Approval manifest/file mismatch; unapproved={missing}, missing_files={stale}.")

    fingerprints: dict[str, str] = {}
    dialogue_files: list[Path] = []
    for path in files:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        entry = approved[path.name]
        digest = sha256_bytes(raw)
        if entry.get("sha256") != digest:
            raise ValueError(f"{path.name}: SHA-256 differs from the approved version.")
        if entry.get("character_count") != len(text):
            raise ValueError(f"{path.name}: character_count differs from the approved version.")
        fingerprints[path.name] = digest
        # Narrative seed text is approved, but is not a user/assistant SFT pair.
        if path.name.startswith("original_dialogue_ar") or path.name.startswith("dialogue_ar"):
            dialogue_files.append(path)

    if not dialogue_files:
        raise ValueError("No approved original_dialogue_ar*.txt files found for supervised fine-tuning.")
    return dialogue_files, fingerprints


def validate_message_content(content: str, source_name: str, block_number: int) -> None:
    """Reject likely personal contact details and credential-like strings."""
    if EMAIL_RE.search(content):
        raise ValueError(f"{source_name}: possible email address in block {block_number}.")
    if EGYPT_MOBILE_RE.search(content):
        raise ValueError(f"{source_name}: possible Egyptian mobile number in block {block_number}.")
    if SECRET_RE.search(content):
        raise ValueError(f"{source_name}: possible credential or secret in block {block_number}.")


def parse_dialogue_text(text: str, source_name: str = "<memory>") -> list[list[dict[str, str]]]:
    """Parse blank-line-separated, alternating Arabic user/Jon2 dialogue blocks."""
    conversations: list[list[dict[str, str]]] = []
    for block_number, block in enumerate(re.split(r"\n\s*\n", text.strip()), 1):
        messages: list[dict[str, str]] = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            matched = False
            for label in USER_LABELS:
                if line.startswith(label):
                    messages.append({"role": "user", "content": line[len(label):].strip()})
                    matched = True
                    break
            if matched:
                continue
            for label in ASSISTANT_LABELS:
                if line.startswith(label):
                    messages.append({"role": "assistant", "content": line[len(label):].strip()})
                    matched = True
                    break
            if not matched:
                raise ValueError(f"{source_name}: unrecognized dialogue line in block {block_number}: {line[:80]!r}")
        if not messages:
            continue
        if len(messages) < 2 or len(messages) % 2:
            raise ValueError(f"{source_name}: block {block_number} must contain complete user/assistant turns.")
        for index, message in enumerate(messages):
            expected = "user" if index % 2 == 0 else "assistant"
            if message["role"] != expected or not message["content"]:
                raise ValueError(f"{source_name}: block {block_number} must alternate non-empty user/assistant turns.")
            validate_message_content(message["content"], source_name, block_number)
        conversations.append(messages)
    return conversations


def collect_conversations(files: list[Path]) -> list[list[dict[str, str]]]:
    all_conversations: list[list[dict[str, str]]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for path in files:
        parsed = parse_dialogue_text(path.read_text(encoding="utf-8", errors="strict"), path.name)
        for conversation in parsed:
            key = tuple((m["role"], m["content"]) for m in conversation)
            if key not in seen:
                seen.add(key)
                all_conversations.append(conversation)
    if not all_conversations:
        raise ValueError("No complete dialogue conversations were found.")
    return all_conversations


def split_conversations(
    conversations: list[list[dict[str, str]]],
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 42,
) -> tuple[list[list[dict[str, str]]], list[list[dict[str, str]]], list[list[dict[str, str]]]]:
    if not 0.05 <= validation_fraction <= 0.2:
        raise ValueError("validation_fraction must be between 0.05 and 0.20.")
    if not 0.05 <= test_fraction <= 0.2:
        raise ValueError("test_fraction must be between 0.05 and 0.20.")
    if validation_fraction + test_fraction >= 0.5:
        raise ValueError("validation_fraction + test_fraction must be below 0.5.")
    if len(conversations) < 20:
        raise ValueError(f"Need at least 20 distinct conversations; found {len(conversations)}.")
    indices = list(range(len(conversations)))
    random.Random(seed).shuffle(indices)
    test_count = max(1, round(len(indices) * test_fraction))
    validation_count = max(1, round(len(indices) * validation_fraction))
    test_set = set(indices[:test_count])
    validation_set = set(indices[test_count:test_count + validation_count])
    train = [item for i, item in enumerate(conversations) if i not in test_set and i not in validation_set]
    validation = [item for i, item in enumerate(conversations) if i in validation_set]
    test = [item for i, item in enumerate(conversations) if i in test_set]
    if not train or not validation or not test:
        raise ValueError("Train, validation, and final test splits must all be non-empty.")
    return train, validation, test


def count_assistant_examples(conversations: list[list[dict[str, str]]]) -> int:
    return sum(1 for conversation in conversations for message in conversation if message["role"] == "assistant")


def prepare_manifest(
    data_dir: Path,
    approval_manifest: Path,
    validation_fraction: float,
    test_fraction: float,
    seed: int,
) -> dict[str, Any]:
    files, fingerprints = load_approved_dialogue_files(data_dir, approval_manifest)
    conversations = collect_conversations(files)
    train, validation, test = split_conversations(
        conversations, validation_fraction, test_fraction, seed
    )
    return {
        "base_model": args.model_name,
        "base_model_license": BASE_MODEL_LICENSE,
        "source_files": fingerprints,
        "conversation_count": len(conversations),
        "assistant_training_examples": count_assistant_examples(conversations),
        "train_conversations": len(train),
        "validation_conversations": len(validation),
        "test_conversations": len(test),
        "train_assistant_examples": count_assistant_examples(train),
        "validation_assistant_examples": count_assistant_examples(validation),
        "test_assistant_examples": count_assistant_examples(test),
        "validation_fraction": validation_fraction,
        "test_fraction": test_fraction,
        "split_seed": seed,
        "training_method": "supervised_fine_tuning_with_peft_lora",
        "adapter_only": True,
        "human_review_required": True,
        "public_release_approved": False,
    }


def build_tokenized_examples(conversations, tokenizer, max_length: int):
    """Mask prompt tokens so the loss updates only assistant responses."""
    rows = []
    for conversation in conversations:
        for end in range(1, len(conversation), 2):
            history = conversation[:end]
            target = conversation[: end + 1]
            prompt_ids = tokenizer.apply_chat_template(
                history, tokenize=True, add_generation_prompt=True
            )
            full_ids = tokenizer.apply_chat_template(
                target, tokenize=True, add_generation_prompt=False
            )
            if hasattr(prompt_ids, "tolist"):
                prompt_ids = prompt_ids.tolist()
            if hasattr(full_ids, "tolist"):
                full_ids = full_ids.tolist()
            if isinstance(prompt_ids, list) and prompt_ids and isinstance(prompt_ids[0], list):
                prompt_ids = prompt_ids[0]
            if isinstance(full_ids, list) and full_ids and isinstance(full_ids[0], list):
                full_ids = full_ids[0]
            if len(full_ids) > max_length:
                overflow = len(full_ids) - max_length
                full_ids = full_ids[overflow:]
                prompt_length = max(0, len(prompt_ids) - overflow)
            else:
                prompt_length = len(prompt_ids)
            prompt_length = min(prompt_length, len(full_ids))
            if prompt_length >= len(full_ids):
                continue
            labels = [-100] * prompt_length + full_ids[prompt_length:]
            rows.append({
                "input_ids": full_ids,
                "attention_mask": [1] * len(full_ids),
                "labels": labels,
            })
    if not rows:
        raise ValueError("No assistant response tokens remain after tokenization/truncation.")
    return rows


def run_training(args) -> int:
    manifest = prepare_manifest(
        Path(args.data), Path(args.approval_manifest), args.validation_fraction,
        args.test_fraction, args.seed
    )
    manifest["base_model"] = args.model_name
    manifest["base_model_license"] = "Apache-2.0"
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    if not args.execute or args.dry_run:
        print("DRY RUN ONLY: no model loaded, no optimizer steps, and no weights changed.")
        return 0

    try:
        import torch
        from unsloth import FastLanguageModel
        from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments
    except ImportError as exc:
        raise RuntimeError(
            "Install ai_engine/requirements-lora.txt in a supported GPU training runtime."
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError(
            "A CUDA GPU is required for Qwen3.5-2B LoRA training. "
            "CPU training is intentionally disabled for this production-oriented run."
        )

    files, fingerprints = load_approved_dialogue_files(Path(args.data), Path(args.approval_manifest))
    conversations = collect_conversations(files)
    train_conversations, validation_conversations, test_conversations = split_conversations(
        conversations, args.validation_fraction, args.test_fraction, args.seed
    )

    # Qwen3.5 uses a hybrid Gated-DeltaNet/attention architecture. Use the
    # maintained Unsloth loader rather than the older AutoModelForCausalLM path.
    # Keep the base in 16-bit; QLoRA 4-bit is not recommended for this family.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=args.max_length,
        load_in_4bit=False,
        load_in_16bit=True,
        full_finetuning=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
        max_seq_length=args.max_length,
    )
    if hasattr(model, "config"):
        model.config.use_cache = False
    model.print_trainable_parameters()

    train_rows = build_tokenized_examples(train_conversations, tokenizer, args.max_length)
    val_rows = build_tokenized_examples(validation_conversations, tokenizer, args.max_length)
    test_rows = build_tokenized_examples(test_conversations, tokenizer, args.max_length)

    class Rows(torch.utils.data.Dataset):
        def __init__(self, rows):
            self.rows = rows
        def __len__(self):
            return len(self.rows)
        def __getitem__(self, index):
            return self.rows[index]

    output_dir = Path(args.output)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output adapter directory is not empty: {output_dir}")
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        seed=args.seed,
        data_seed=args.seed,
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=Rows(train_rows),
        eval_dataset=Rows(val_rows),
        data_collator=DataCollatorForSeq2Seq(
            tokenizer=tokenizer, model=model, padding=True, label_pad_token_id=-100
        ),
    )
    result = trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    validation_eval = trainer.evaluate(eval_dataset=Rows(val_rows), metric_key_prefix="validation")
    final_test_eval = trainer.evaluate(eval_dataset=Rows(test_rows), metric_key_prefix="test")

    gguf_dir = None
    if args.export_gguf:
        gguf_dir = output_dir / "gguf"
        model.save_pretrained_gguf(
            str(gguf_dir), tokenizer, quantization_method=args.gguf_quantization
        )

    metadata = {
        **manifest,
        "base_model": args.model_name,
        "source_files": fingerprints,
        "train_result": result.metrics,
        "validation_evaluation": validation_eval,
        "final_held_out_test_evaluation": final_test_eval,
        "lora_rank": args.lora_rank,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "max_length": args.max_length,
        "epochs": args.epochs,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "adapter_directory": str(output_dir),
        "gguf_directory": str(gguf_dir) if gguf_dir else None,
        "gguf_quantization": args.gguf_quantization if gguf_dir else None,
        "optimizer_steps_completed": trainer.state.global_step,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "training_completed": True,
        "human_review_required": True,
        "public_release_approved": False,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "jon2_lora_training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Rights-gated Qwen3.5-2B Arabic LoRA fine-tuning for Jon2.")
    parser.add_argument("--model-name", default=BASE_MODEL)
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--approval-manifest", default="ai_engine/training_data/source_approvals.json")
    parser.add_argument("--output", default="artifacts/jon2-qwen35-2b-lora")
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--test-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.0)
    parser.add_argument("--export-gguf", action="store_true", help="Also export a Q4_K_M GGUF for the CPU inference server.")
    parser.add_argument("--gguf-quantization", default="q4_k_m", choices=["q4_k_m", "q5_k_m", "q8_0", "f16"])
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument("--execute", action="store_true", help="Actually load Qwen3.5 and perform optimizer steps.")
    run_mode.add_argument("--dry-run", action="store_true", help="Validate rights, data, and split only; this is also the default.")
    return parser

def main():
    args = build_parser().parse_args()
    if args.max_length < 128 or args.batch_size < 1 or args.gradient_accumulation < 1:
        raise SystemExit("max-length must be >=128 and batch/gradient-accumulation must be positive.")
    if args.epochs <= 0 or args.learning_rate <= 0 or args.lora_rank < 1 or args.lora_alpha < 1:
        raise SystemExit("epochs, learning rate, LoRA rank, and alpha must be positive.")
    return run_training(args)


if __name__ == "__main__":
    raise SystemExit(main())
