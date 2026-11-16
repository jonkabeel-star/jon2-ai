"""QLoRA fine-tuning for Jon2 on Qwen3.5-9B.

Fail-closed: CUDA only, separately approved train/eval JSONL, exact SHA-256
source manifests, held-out leakage checks, assistant-only loss, private adapter.
This does not create a standalone foundation model or a production server.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
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
        if any(not isinstance(m, dict) or m.get("role") not in {"user", "assistant"}
               or not isinstance(m.get("content"), str) or not m["content"].strip()
               for m in messages):
            raise ValueError(f"{path.name}:{line_no}: invalid user/assistant message.")
        if messages[0]["role"] != "user" or messages[-1]["role"] != "assistant":
            raise ValueError(f"{path.name}:{line_no}: conversation must start user and end assistant.")
        if any(messages[i]["role"] == messages[i - 1]["role"] for i in range(1, len(messages))):
            raise ValueError(f"{path.name}:{line_no}: roles must alternate user/assistant.")
        rows.append({"messages": messages})
    return rows


def conversation_fingerprint(row: dict) -> str:
    canonical = json.dumps(row["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--train-approval-manifest", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--eval-approval-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-seq-length", type=int, default=512)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--resume-from-checkpoint", type=str, default=None)
    args = parser.parse_args()

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. CPU fallback is disabled; no training started.")
    if args.max_seq_length < 256 or args.max_seq_length > 1024:
        raise ValueError("max-seq-length must be between 256 and 1024 for the T4 preflight profile.")
    if args.epochs <= 0 or args.learning_rate <= 0 or args.lora_r < 4:
        raise ValueError("Invalid training hyperparameters.")

    workspace = Path(os.environ.get("GITHUB_WORKSPACE", "/kaggle/working")).resolve()
    paths = [
        ("training data", args.train_dir), ("evaluation data", args.eval_dir),
        ("training approval manifest", args.train_approval_manifest),
        ("evaluation approval manifest", args.eval_approval_manifest),
        ("adapter output", args.output_dir),
    ]
    for label, path in paths:
        resolved = path.resolve()
        if resolved == workspace or workspace in resolved.parents:
            raise PermissionError(f"{label} must be outside the repository/workspace checkout: {resolved}")
    if args.train_dir.resolve() == args.eval_dir.resolve():
        raise PermissionError("Training and held-out evaluation directories must be separate.")
    if args.output_dir.resolve() in {args.train_dir.resolve(), args.eval_dir.resolve()}:
        raise PermissionError("Adapter output must be separate from both data directories.")

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from source_approval import validate_source_approvals
    validate_source_approvals(args.train_dir, args.train_approval_manifest, include_jsonl=True)
    validate_source_approvals(args.eval_dir, args.eval_approval_manifest, include_jsonl=True)

    train_files = sorted(args.train_dir.rglob("*.jsonl"))
    eval_files = sorted(args.eval_dir.rglob("*.jsonl"))
    if not train_files or not eval_files:
        raise FileNotFoundError("Both private train-dir and held-out eval-dir need JSONL files.")
    train_rows = [row for path in train_files for row in load_jsonl(path)]
    eval_rows = [row for path in eval_files for row in load_jsonl(path)]
    if len(train_rows) < 100 or len(eval_rows) < 30:
        raise ValueError(f"Need >=100 approved train and >=30 approved held-out examples; got {len(train_rows)} and {len(eval_rows)}.")
    train_ids = {conversation_fingerprint(row) for row in train_rows}
    eval_ids = {conversation_fingerprint(row) for row in eval_rows}
    if train_ids & eval_ids:
        raise ValueError(f"Data leakage: {len(train_ids & eval_ids)} exact conversations overlap.")
    if len(train_ids) != len(train_rows) or len(eval_ids) != len(eval_rows):
        raise ValueError("Duplicate conversations detected; deduplicate before training.")

    from datasets import Dataset
    from transformers import AutoTokenizer, Qwen3_5ForCausalLM, BitsAndBytesConfig, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if "eval_strategy" not in inspect.signature(TrainingArguments.__init__).parameters:
        raise RuntimeError("Installed Transformers lacks TrainingArguments.eval_strategy; install a current Qwen3.5-compatible build.")
    print("GPUs:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"GPU {i}: {props.name} | {props.total_memory / 1024**3:.2f} GiB")
    print("Base:", MODEL_ID, "| training on GPU 0 only to avoid unsupported multi-GPU device_map training.")

    compute_dtype = torch.float16
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=compute_dtype,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    model = Qwen3_5ForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=quant, device_map={"": 0},
        torch_dtype=compute_dtype, low_cpu_mem_usage=True,
        trust_remote_code=False, attn_implementation="sdpa",
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    candidate_targets = {
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
        "in_proj_qkv", "in_proj_z", "in_proj_a", "in_proj_b", "out_proj",
    }
    linear_suffixes = set()
    for name, module in model.named_modules():
        if hasattr(module, "weight") and module.__class__.__name__.lower().find("linear") >= 0:
            linear_suffixes.add(name.rsplit(".", 1)[-1])
    targets = sorted(candidate_targets & linear_suffixes)
    if not targets:
        raise RuntimeError("No supported Qwen3.5 linear target modules found; refusing to train with an empty LoRA target set.")
    print("LoRA target modules:", targets)
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_r * 2, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM", target_modules=targets,
    ))
    model.print_trainable_parameters()

    def encode(row):
        messages = row["messages"]
        ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=False, enable_thinking=False,
        )
        labels = [-100] * len(ids)
        for index, message in enumerate(messages):
            if message["role"] != "assistant":
                continue
            prefix_ids = tokenizer.apply_chat_template(
                messages[:index], tokenize=True, add_generation_prompt=True, enable_thinking=False,
            )
            through_ids = tokenizer.apply_chat_template(
                messages[:index + 1], tokenize=True, add_generation_prompt=False, enable_thinking=False,
            )
            start, end = min(len(prefix_ids), len(ids)), min(len(through_ids), len(ids))
            if end > start:
                labels[start:end] = ids[start:end]
        ids, labels = ids[:args.max_seq_length], labels[:args.max_seq_length]
        if not any(token != -100 for token in labels):
            raise ValueError("Example has no assistant-only target tokens after tokenization/truncation.")
        return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels}

    train_ds = Dataset.from_list(train_rows).map(encode, remove_columns=["messages"])
    eval_ds = Dataset.from_list(eval_rows).map(encode, remove_columns=["messages"])

    def collate(features):
        max_len = max(len(x["input_ids"]) for x in features)
        pad_id = tokenizer.pad_token_id
        input_ids, masks, labels = [], [], []
        for item in features:
            pad = max_len - len(item["input_ids"])
            input_ids.append(item["input_ids"] + [pad_id] * pad)
            masks.append(item["attention_mask"] + [0] * pad)
            labels.append(item["labels"] + [-100] * pad)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(masks, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "trainer_checkpoints"),
        num_train_epochs=args.epochs, max_steps=args.max_steps,
        learning_rate=args.learning_rate, per_device_train_batch_size=1,
        per_device_eval_batch_size=1, gradient_accumulation_steps=8,
        gradient_checkpointing=True, fp16=True, bf16=False,
        optim="paged_adamw_8bit", lr_scheduler_type="cosine", warmup_ratio=0.03,
        logging_steps=10, eval_strategy="steps", eval_steps=25,
        save_strategy="steps", save_steps=25, save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        greater_is_better=False, report_to="none", remove_unused_columns=False,
        dataloader_pin_memory=True,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_ds,
                      eval_dataset=eval_ds, data_collator=collate)
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    evaluation = trainer.evaluate()

    adapter_dir = args.output_dir / "jon2-qwen35-9b-lora"
    model.save_pretrained(adapter_dir, safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)
    files = {
        path.relative_to(adapter_dir).as_posix(): {
            "size_bytes": path.stat().st_size, "sha256": sha256(path)
        }
        for path in sorted(adapter_dir.rglob("*")) if path.is_file()
    }
    manifest = {
        "format": "jon2-qwen35-lora-manifest-v2",
        "base_model": MODEL_ID, "base_model_is_third_party": True,
        "jon2_artifact": "LoRA adapter only; base model weights are not copied",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
        "training_conversations": len(train_rows), "held_out_conversations": len(eval_rows),
        "eval_metrics": {k: float(v) for k, v in evaluation.items() if isinstance(v, (int, float))},
        "train_files": {p.name: sha256(p) for p in train_files},
        "eval_files": {p.name: sha256(p) for p in eval_files},
        "files": files, "public_release_approved": False, "human_review_required": True,
    }
    (adapter_dir / "jon2-adapter-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Training finished. Private adapter saved; production serving/public release remain disabled.")


if __name__ == "__main__":
    main()
