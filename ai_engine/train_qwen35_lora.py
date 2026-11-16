"""QLoRA fine-tuning entry point for Jon2's Qwen3.5-9B foundation.

Fail-closed: CUDA only; exact private source approvals required; train/eval
files must live outside the repository; held-out data is never trained on.
This creates a private adapter, not a from-scratch model or a production server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "Qwen/Qwen3.5-9B"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        messages = item.get("messages") if isinstance(item, dict) else None
        if not isinstance(messages, list) or len(messages) < 2:
            raise ValueError(f"{path.name}:{line_no}: expected messages list.")
        if any(
            not isinstance(m, dict)
            or m.get("role") not in {"user", "assistant"}
            or not isinstance(m.get("content"), str)
            or not m["content"].strip()
            for m in messages
        ):
            raise ValueError(f"{path.name}:{line_no}: invalid user/assistant message.")
        if not any(m["role"] == "user" for m in messages) or not any(m["role"] == "assistant" for m in messages):
            raise ValueError(f"{path.name}:{line_no}: both roles are required.")
        rows.append({"messages": messages})
    return rows


def conversation_fingerprint(row: dict) -> str:
    canonical = json.dumps(row["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=0)
    args = parser.parse_args()

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. CPU fallback is disabled; no training started.")
    if args.max_seq_length < 256 or args.max_seq_length > 4096:
        raise ValueError("max-seq-length must be between 256 and 4096.")
    if args.epochs <= 0 or args.learning_rate <= 0 or args.lora_r < 4:
        raise ValueError("Invalid training hyperparameters.")

    repo = Path(os.environ.get("GITHUB_WORKSPACE", "/kaggle/working")).resolve()
    for label, path in (("training data", args.train_dir), ("evaluation data", args.eval_dir),
                        ("approval manifest", args.approval_manifest), ("adapter output", args.output_dir)):
        resolved = path.resolve()
        if resolved == repo or repo in resolved.parents:
            raise PermissionError(f"{label} must be outside the repository/workspace checkout: {resolved}")
    if args.train_dir.resolve() == args.eval_dir.resolve():
        raise PermissionError("Training and held-out evaluation directories must be separate.")
    if args.output_dir.resolve() == args.train_dir.resolve() or args.output_dir.resolve() == args.eval_dir.resolve():
        raise PermissionError("Adapter output must be separate from both data directories.")

    # Reuse the repository's exact-file, SHA-256, rights, and JSONL approval gate.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from source_approval import validate_source_approvals
    validate_source_approvals(args.train_dir, args.approval_manifest, include_jsonl=True)

    train_files = sorted(args.train_dir.rglob("*.jsonl"))
    eval_files = sorted(args.eval_dir.rglob("*.jsonl"))
    if not train_files or not eval_files:
        raise FileNotFoundError("Both private train-dir and held-out eval-dir need JSONL files.")
    train_rows = [row for path in train_files for row in load_jsonl(path)]
    eval_rows = [row for path in eval_files for row in load_jsonl(path)]
    if len(train_rows) < 100:
        raise ValueError(f"Only {len(train_rows)} training conversations; need at least 100 reviewed examples before QLoRA.")
    if len(eval_rows) < 30:
        raise ValueError(f"Only {len(eval_rows)} held-out conversations; need at least 30.")
    train_ids = {conversation_fingerprint(row) for row in train_rows}
    eval_ids = {conversation_fingerprint(row) for row in eval_rows}
    overlap = train_ids & eval_ids
    if overlap:
        raise ValueError(f"Data leakage: {len(overlap)} exact conversations appear in both train and held-out sets.")
    if len(train_ids) < len(train_rows):
        raise ValueError("Duplicate training conversations detected; deduplicate before training.")

    from datasets import Dataset
    from transformers import (
        AutoTokenizer, Qwen3_5ForCausalLM, BitsAndBytesConfig,
        Trainer, TrainingArguments, DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM GiB:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))
    print("Base:", MODEL_ID)
    print(f"Train conversations: {len(train_rows)} | Held-out: {len(eval_rows)}")
    compute_dtype = torch.float16
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=compute_dtype,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = Qwen3_5ForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=quant, device_map="auto",
        torch_dtype=compute_dtype, low_cpu_mem_usage=True,
        trust_remote_code=False, attn_implementation="sdpa",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_r * 2, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    def encode(row):
        text = tokenizer.apply_chat_template(
            row["messages"], tokenize=False, add_generation_prompt=False,
            enable_thinking=False,
        )
        encoded = tokenizer(text, truncation=True, max_length=args.max_seq_length, padding=False)
        encoded["labels"] = list(encoded["input_ids"])
        return encoded

    train_ds = Dataset.from_list(train_rows).map(encode, remove_columns=["messages"])
    eval_ds = Dataset.from_list(eval_rows).map(encode, remove_columns=["messages"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "trainer_tmp"),
        num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.learning_rate, per_device_train_batch_size=1,
        per_device_eval_batch_size=1, gradient_accumulation_steps=8,
        gradient_checkpointing=True, fp16=True, bf16=False,
        optim="paged_adamw_8bit", lr_scheduler_type="cosine", warmup_ratio=0.03,
        logging_steps=10, eval_strategy="steps", eval_steps=50,
        save_strategy="steps", save_steps=50, save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, report_to="none",
        remove_unused_columns=False, dataloader_pin_memory=True,
    )
    trainer = Trainer(
        model=model, args=training_args, train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    trainer.evaluate()
    adapter_dir = args.output_dir / "jon2-qwen35-9b-lora"
    model.save_pretrained(adapter_dir, safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)

    files = {}
    for path in sorted(adapter_dir.rglob("*")):
        if path.is_file():
            files[path.relative_to(adapter_dir).as_posix()] = {
                "size_bytes": path.stat().st_size, "sha256": sha256(path)
            }
    manifest = {
        "format": "jon2-qwen35-lora-manifest-v1",
        "base_model": MODEL_ID,
        "base_model_is_third_party": True,
        "jon2_artifact": "LoRA adapter only; base model weights are not copied",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
        "training_conversations": len(train_rows), "held_out_conversations": len(eval_rows),
        "train_files": {p.name: sha256(p) for p in train_files},
        "eval_files": {p.name: sha256(p) for p in eval_files},
        "files": files, "public_release_approved": False,
        "human_review_required": True,
    }
    (adapter_dir / "jon2-adapter-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Training complete. Adapter is private; serving and public release are NOT enabled.")


if __name__ == "__main__":
    main()
