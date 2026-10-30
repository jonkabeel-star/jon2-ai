"""Modern training entry point for the original Jon2 Transformer.

Features: warmup + cosine learning-rate decay, CUDA mixed precision when
available, gradient clipping, validation-based best-checkpoint selection,
early stopping, and resumable training. No pretrained model is downloaded.
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

import torch
from torch import nn

from jon2_core import (
    Jon2Transformer,
    _batch,
    _estimate_loss,
    read_corpus,
)
from tokenizer import ByteBPETokenizer


def save_checkpoint(path: Path, model, tokenizer, args, step, best_val, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "model_state": model.state_dict(),
            "tokenizer": tokenizer.to_dict(),
            "config": config,
            "training_steps": step,
            "best_validation_loss": best_val,
            "corpus_characters": args.corpus_characters,
            "validation_fraction": args.validation_fraction,
            "model_name": "Jon2 Original Transformer",
            "training_method": "warmup_cosine_amp_early_stopping",
        },
        temporary,
    )
    temporary.replace(path)


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_enabled = device.type == "cuda" and not args.no_amp

    corpus = read_corpus(Path(args.data))
    tokenizer = ByteBPETokenizer.train(corpus, vocab_size=args.tokenizer_vocab_size, min_frequency=args.tokenizer_min_frequency)
    encoded = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    args.corpus_characters = len(corpus)

    if len(corpus) < args.minimum_chars:
        raise ValueError(
            f"Training corpus has {len(corpus):,} characters; this run requires "
            f"at least {args.minimum_chars:,}. Add reviewed, project-owned or "
            "properly licensed data. Do not duplicate text to pass this check."
        )
    if len(encoded) <= args.context * 2 + 2:
        raise ValueError("Corpus is too short for the selected context window.")

    split = int(len(encoded) * (1.0 - args.validation_fraction))
    train_data, val_data = encoded[:split], encoded[split:]
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
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )

    start_step = 0
    best_val = float("inf")
    stale_evaluations = 0
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")
        saved = torch.load(resume_path, map_location=device, weights_only=False)
        if saved.get("tokenizer") != tokenizer.to_dict() or saved.get("config") != config:
            raise ValueError("Resume checkpoint vocabulary/config does not match this run.")
        model.load_state_dict(saved["model_state"])
        if "optimizer_state" in saved:
            optimizer.load_state_dict(saved["optimizer_state"])
        start_step = int(saved.get("training_steps", 0))
        best_val = float(saved.get("best_validation_loss", float("inf")))
        print(f"Resuming from step {start_step}; best validation loss={best_val:.4f}")

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
    if start_step:
        for _ in range(start_step):
            scheduler.step()

    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)
    print(
        f"Jon2 original training | device={device} | AMP={amp_enabled} | "
        f"tokens={len(encoded):,} | vocab={tokenizer.vocab_size}"
    )
    if len(encoded) < 500_000:
        print("CAUTION: corpus remains small for a general-purpose assistant.")

    best_path = Path(args.output)
    last_path = Path(args.last_checkpoint)
    evaluations_without_improvement = 0

    for step in range(start_step, args.steps):
        model.train()
        x, y = _batch(train_data, args.context, args.batch_size, device)
        optimizer.zero_grad(set_to_none=True)

        with torch.cuda.amp.autocast(enabled=amp_enabled):
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
                save_checkpoint(best_path, model.cpu(), tokenizer, args,
                                completed_step, best_val, config)
                model.to(device)
                print(f"Saved new best checkpoint: {best_path}")
            else:
                evaluations_without_improvement += 1

            if args.keep_last:
                last_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "tokenizer": tokenizer.to_dict(),
                        "config": config,
                        "training_steps": completed_step,
                        "best_validation_loss": best_val,
                        "optimizer_state": optimizer.state_dict(),
                    },
                    last_path,
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
    parser.add_argument("--output", default="ai_engine/checkpoints/jon2-small.pt")
    parser.add_argument("--last-checkpoint", default="ai_engine/checkpoints/jon2-last.pt")
    parser.add_argument("--resume", default="")
    parser.add_argument("--steps", type=int, default=10000)
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
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-amp", action="store_true")
    parser.add_argument("--keep-last", action="store_true")
    args = parser.parse_args()

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
