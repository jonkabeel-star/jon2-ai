"""Modern training entry point for the original Jon2 Transformer.

Features: warmup + cosine learning-rate decay, CUDA mixed precision when
available, gradient clipping, validation-based best-checkpoint selection,
early stopping, and exact resumable training state. No pretrained model is downloaded.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import random
from pathlib import Path

import torch
from torch import nn

from jon2_core import Jon2Transformer, _batch, _estimate_loss, read_corpus
from tokenizer import ByteBPETokenizer
from source_approval import validate_source_approvals
from model_profiles import PROFILES, describe_profile


def split_corpus_blocks(corpus: str, validation_fraction: float, seed: int):
    """Split blank-line-delimited text blocks before fitting the tokenizer."""
    if not isinstance(corpus, str) or not corpus.strip():
        raise ValueError("Training corpus must be non-empty text.")
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("validation_fraction must be between 0.05 and 0.4.")
    blocks = [block.strip() for block in __import__("re").split(r"\n\s*\n", corpus) if block.strip()]
    if len(blocks) < 2:
        raise ValueError(
            "At least two blank-line-delimited text blocks are required for a "
            "held-out validation split."
        )
    indices = list(range(len(blocks)))
    random.Random(seed).shuffle(indices)
    validation_count = max(1, math.ceil(len(blocks) * validation_fraction))
    if validation_count >= len(blocks):
        raise ValueError("Not enough independent text blocks for train/validation.")
    validation_indices = set(indices[:validation_count])
    train_text = "\n\n".join(
        block for index, block in enumerate(blocks) if index not in validation_indices
    )
    validation_text = "\n\n".join(
        block for index, block in enumerate(blocks) if index in validation_indices
    )
    return train_text, validation_text


def _training_plan(args):
    names = (
        "steps", "batch_size", "context", "width", "heads", "layers",
        "dropout", "learning_rate", "weight_decay", "warmup_steps",
        "validation_fraction", "eval_steps", "eval_every", "patience",
        "min_delta", "grad_clip", "minimum_chars", "tokenizer_vocab_size",
        "tokenizer_min_frequency", "seed", "no_amp",
    )
    plan = {name: getattr(args, name) for name in names}
    plan["validation_split_algorithm"] = "seeded_paragraph_blocks_v1"
    if getattr(args, "minimum_tokens_per_parameter", 0) > 0:
        plan["minimum_tokens_per_parameter"] = args.minimum_tokens_per_parameter
    return plan


def restore_scheduler_state(scheduler, optimizer, state):
    """Restore scheduler internals and the optimizer's active learning rate."""
    scheduler.load_state_dict(state)
    for group, learning_rate in zip(optimizer.param_groups, scheduler.get_last_lr()):
        group["lr"] = learning_rate


def save_checkpoint(
    path: Path, model, tokenizer, args, step, best_val, config,
    optimizer=None, scheduler=None, scaler=None, corpus_sha256=None,
    evaluations_without_improvement=0,
):
    """Atomically save model, optimizer, scheduler, scaler, and RNG states."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    state = {
        "model_state": model.state_dict(),
        "tokenizer": tokenizer.to_dict(),
        "config": config,
        "training_plan": _training_plan(args),
        "training_steps": step,
        "best_validation_loss": best_val,
        "evaluations_without_improvement": evaluations_without_improvement,
        "corpus_characters": args.corpus_characters,
        "corpus_sha256": corpus_sha256,
        "validation_fraction": args.validation_fraction,
        "model_name": "Jon2 Original Transformer",
        "training_method": "warmup_cosine_amp_early_stopping",
        "python_rng_state": random.getstate(),
        "torch_rng_state": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["cuda_rng_state_all"] = torch.cuda.get_rng_state_all()
    if optimizer is not None:
        state["optimizer_state"] = optimizer.state_dict()
    if scheduler is not None:
        state["scheduler_state"] = scheduler.state_dict()
    if scaler is not None:
        state["scaler_state"] = scaler.state_dict()

    torch.save(state, temporary)
    temporary.replace(path)


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_enabled = device.type == "cuda" and not args.no_amp

    data_dir = Path(args.data)
    validate_source_approvals(data_dir, Path(args.approval_manifest))
    corpus = read_corpus(data_dir)
    args.corpus_characters = len(corpus)
    if len(corpus) < args.minimum_chars:
        raise ValueError(
            f"Training corpus has {len(corpus):,} characters; this run requires "
            f"at least {args.minimum_chars:,}. Add reviewed, project-owned or "
            "properly licensed data. Do not duplicate text to pass this check."
        )

    corpus_sha256 = hashlib.sha256(corpus.encode("utf-8")).hexdigest()
    train_text, validation_text = split_corpus_blocks(
        corpus, args.validation_fraction, args.seed
    )
    # Fit vocabulary/merges on training text only: validation data stays unseen.
    tokenizer = ByteBPETokenizer.train(
        train_text,
        vocab_size=args.tokenizer_vocab_size,
        min_frequency=args.tokenizer_min_frequency,
    )
    train_data = torch.tensor(tokenizer.encode(train_text), dtype=torch.long)
    val_data = torch.tensor(tokenizer.encode(validation_text), dtype=torch.long)

    if len(train_data) <= args.context + 1:
        raise ValueError("Training partition is too short for the selected context window.")
    if len(val_data) <= args.context + 1:
        raise ValueError("Validation partition is too short.")

    config = {
        "width": args.width,
        "heads": args.heads,
        "layers": args.layers,
        "context": args.context,
        "dropout": args.dropout,
    }
    model = Jon2Transformer(vocab_size=tokenizer.vocab_size, **config).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    corpus_tokens = len(train_data) + len(val_data)
    tokens_per_parameter = corpus_tokens / max(1, parameter_count)
    print(
        f"Model parameters={parameter_count:,} | approved_corpus_tokens={corpus_tokens:,} | "
        f"tokens_per_parameter={tokens_per_parameter:.4f}"
    )
    if args.minimum_tokens_per_parameter and tokens_per_parameter < args.minimum_tokens_per_parameter:
        raise ValueError(
            f"Insufficient approved training data for profile '{args.profile}': "
            f"{tokens_per_parameter:.4f} tokens/parameter; "
            f"minimum required is {args.minimum_tokens_per_parameter}. "
            "Add diverse, rights-approved Arabic data. Do not duplicate text or lower this guard."
        )

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )

    start_step = 0
    best_val = float("inf")
    evaluations_without_improvement = 0
    saved = None
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")
        saved = torch.load(resume_path, map_location=device, weights_only=True)
        if saved.get("tokenizer") != tokenizer.to_dict() or saved.get("config") != config:
            raise ValueError("Resume checkpoint vocabulary/config does not match this run.")
        if saved.get("corpus_sha256") and saved["corpus_sha256"] != corpus_sha256:
            raise ValueError("Resume checkpoint was created from different training text.")
        saved_plan = saved.get("training_plan")
        if saved_plan is not None:
            # Total target steps may grow between daily continuation cycles.
            saved_plan = dict(saved_plan)
            saved_plan.pop("steps", None)
        if saved_plan is not None and saved_plan != _training_plan(args):
            raise ValueError(
                "Resume training settings differ from the saved run. "
                "Use the same settings to continue exactly, or start a new run."
            )
        model.load_state_dict(saved["model_state"])
        if "optimizer_state" in saved:
            optimizer.load_state_dict(saved["optimizer_state"])
        start_step = int(saved.get("training_steps", 0))
        best_val = float(saved.get("best_validation_loss", float("inf")))
        evaluations_without_improvement = int(saved.get("evaluations_without_improvement", 0))
        if args.reset_early_stopping:
            evaluations_without_improvement = 0
        if evaluations_without_improvement < 0:
            raise ValueError("Resume checkpoint has an invalid early-stopping counter.")
        if args.additional_steps:
            args.steps = start_step + args.additional_steps
            print(f"Daily continuation target: {start_step} + {args.additional_steps} = {args.steps} steps")
        print(
            f"Resuming from step {start_step}; best validation loss={best_val:.4f}; "
            f"evaluations without improvement={evaluations_without_improvement}"
        )

    def lr_at(step):
        if step < args.warmup_steps:
            return max(1, step + 1) / max(1, args.warmup_steps)
        progress = min(
            1.0,
            (step - args.warmup_steps) /
            max(1, args.steps - args.warmup_steps),
        )
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_at)
    if saved and "scheduler_state" in saved:
        restore_scheduler_state(scheduler, optimizer, saved["scheduler_state"])
    elif start_step:
        print("Legacy checkpoint: scheduler state unavailable; using step-based fallback.")
        for _ in range(start_step):
            scheduler.step()

    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    if saved and "scaler_state" in saved:
        scaler.load_state_dict(saved["scaler_state"])

    # Restore RNG only after model/optimizer/scheduler/scaler initialization.
    if saved:
        if "python_rng_state" in saved:
            random.setstate(saved["python_rng_state"])
        if "torch_rng_state" in saved:
            torch.set_rng_state(saved["torch_rng_state"].cpu())
        if torch.cuda.is_available() and "cuda_rng_state_all" in saved:
            torch.cuda.set_rng_state_all(saved["cuda_rng_state_all"])

    print(
        f"Jon2 original training | device={device} | AMP={amp_enabled} | "
        f"train_tokens={len(train_data):,} | validation_tokens={len(val_data):,} | "
        f"vocab={tokenizer.vocab_size}"
    )
    if (len(train_data) + len(val_data)) < 500_000:
        print("CAUTION: corpus remains small for a general-purpose assistant.")

    best_path = Path(args.output)
    last_path = Path(args.last_checkpoint)

    for step in range(start_step, args.steps):
        model.train()
        x, y = _batch(train_data, args.context, args.batch_size, device)
        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast(device_type="cuda", enabled=amp_enabled):
            logits = model(x)
            loss = nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)), y.reshape(-1)
            )

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        completed_step = step + 1
        if completed_step == 1 or completed_step % args.eval_every == 0 or completed_step == args.steps:
            scores = _estimate_loss(
                model, train_data, val_data, args.context, args.batch_size,
                device, args.eval_steps,
            )
            current_lr = optimizer.param_groups[0]["lr"]
            print(
                f"step {completed_step}/{args.steps} | "
                f"train={scores['train']:.4f} | val={scores['validation']:.4f} | "
                f"lr={current_lr:.2e}"
            )

            if scores["validation"] < best_val - args.min_delta:
                best_val = scores["validation"]
                evaluations_without_improvement = 0
                save_checkpoint(
                    best_path, model, tokenizer, args, completed_step,
                    best_val, config, optimizer, scheduler, scaler, corpus_sha256,
                    evaluations_without_improvement=0,
                )
                print(f"Saved new best checkpoint: {best_path}")
            else:
                evaluations_without_improvement += 1

            if args.keep_last:
                save_checkpoint(
                    last_path, model, tokenizer, args, completed_step,
                    best_val, config, optimizer, scheduler, scaler, corpus_sha256,
                    evaluations_without_improvement=evaluations_without_improvement,
                )

            if evaluations_without_improvement >= args.patience:
                print("Early stopping: validation loss did not improve.")
                break

    if not best_path.is_file():
        raise RuntimeError("No best checkpoint was saved; training did not complete an evaluation.")
    print(f"Best checkpoint: {best_path} | validation_loss={best_val:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Train Jon2 with modern training safeguards.")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--approval-manifest", default="ai_engine/training_data/source_approvals.json")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="", help="Select a scalable Jon2 architecture preset.")
    parser.add_argument("--output", default=None, help="Best checkpoint path; profile-specific path is selected by default.")
    parser.add_argument("--last-checkpoint", default=None, help="Resumable checkpoint path; profile-specific path is selected by default.")
    parser.add_argument("--resume", default="")
    parser.add_argument("--steps", type=int, default=10000, help="Total target steps for a new run.")
    parser.add_argument("--additional-steps", type=int, default=0, help="When resuming, add this many steps to the saved global step.")
    parser.add_argument("--reset-early-stopping", action="store_true", help="Reset the no-improvement counter for a new scheduled continuation cycle.")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--context", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--warmup-steps", type=int, default=500)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--eval-steps", type=int, default=20)
    parser.add_argument("--eval-every", type=int, default=250)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--min-delta", type=float, default=0.001)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--minimum-chars", type=int, default=100_000)
    parser.add_argument("--tokenizer-vocab-size", type=int, default=512)
    parser.add_argument("--tokenizer-min-frequency", type=int, default=2)
    parser.add_argument("--minimum-tokens-per-parameter", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-amp", action="store_true")
    parser.add_argument("--keep-last", action="store_true")
    args = parser.parse_args()

    if args.profile:
        selected = describe_profile(args.profile)
        args.width = selected["width"]
        args.heads = selected["heads"]
        args.layers = selected["layers"]
        args.context = selected["context"]
        args.batch_size = selected["batch_size"]
        args.tokenizer_vocab_size = selected["tokenizer_vocab_size"]
        if args.minimum_tokens_per_parameter is None:
            args.minimum_tokens_per_parameter = 10.0
        print(
            f"Selected profile={args.profile} | "
            f"estimated_parameters={selected['estimated_parameters']:,} | "
            f"fp32_weights_gib={selected['estimated_fp32_weights_gib']}"
        )
        print("Profile selection configures a new model; it does not create trained weights.")

    if args.additional_steps < 0:
        parser.error("additional-steps cannot be negative")
    if args.additional_steps and not args.resume:
        parser.error("additional-steps requires --resume")
    if args.minimum_tokens_per_parameter is None:
        args.minimum_tokens_per_parameter = 0.0
    if args.minimum_tokens_per_parameter < 0:
        parser.error("minimum-tokens-per-parameter cannot be negative")

    if args.output is None:
        suffix = args.profile or "small"
        args.output = f"ai_engine/checkpoints/jon2-{suffix}.pt"
    if args.last_checkpoint is None:
        suffix = args.profile or "small"
        args.last_checkpoint = f"ai_engine/checkpoints/jon2-{suffix}-last.pt"

    positive = [
        args.steps, args.batch_size, args.context, args.width, args.heads,
        args.layers, args.eval_steps, args.eval_every, args.patience,
        args.minimum_chars, args.tokenizer_vocab_size, args.tokenizer_min_frequency,
    ]
    if min(positive) <= 0:
        parser.error("training sizes, intervals, and patience must be positive")
    if args.width % args.heads:
        parser.error("width must be divisible by heads")
    if args.warmup_steps < 0 or args.weight_decay < 0 or args.grad_clip <= 0:
        parser.error("warmup must be nonnegative; weight decay and grad clip must be valid")
    if not 0.05 <= args.validation_fraction <= 0.4:
        parser.error("validation-fraction must be between 0.05 and 0.4")
    train(args)


if __name__ == "__main__":
    main()
