"""Train the original Jon2 Transformer with assistant-only dialogue loss.

This is a separate, opt-in training entry point. It requires explicit approval
for every exact source file, keeps held-out conversations separate, uses no
pretrained model, and never calls an external inference API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import torch
from torch import nn

from jon2_core import Jon2Transformer
from tokenizer import ByteBPETokenizer
from source_approval import validate_source_approvals
from dialogue_objective import (
    assistant_only_batch,
    encode_assistant_only,
    estimate_assistant_loss,
    format_dialogues,
    load_dialogue_records,
    masked_language_model_loss,
    split_dialogues,
)


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    data_dir = Path(args.data)
    # This validates every .txt and .jsonl file under the selected folder.
    # Unapproved JSONL sources block training; no implicit approval is granted.
    validate_source_approvals(
        data_dir, Path(args.approval_manifest), include_jsonl=True
    )
    conversations = load_dialogue_records(data_dir)
    train_conversations, validation_conversations = split_dialogues(
        conversations, args.validation_fraction, args.seed
    )
    train_text = format_dialogues(train_conversations)
    tokenizer = ByteBPETokenizer.train(
        train_text,
        vocab_size=args.tokenizer_vocab_size,
        min_frequency=args.tokenizer_min_frequency,
    )
    train_data, train_mask = encode_assistant_only(train_conversations, tokenizer)
    validation_data, validation_mask = encode_assistant_only(
        validation_conversations, tokenizer
    )
    if min(len(train_data), len(validation_data)) <= args.context + 1:
        raise ValueError("Train and validation dialogue streams must exceed context + 1 tokens.")
    if not train_mask[1:].any() or not validation_mask[1:].any():
        raise ValueError("Both train and validation splits need assistant response targets.")

    config = {
        "width": args.width,
        "heads": args.heads,
        "layers": args.layers,
        "context": args.context,
        "dropout": args.dropout,
    }
    model = Jon2Transformer(
        vocab_size=tokenizer.vocab_size, **config
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    device = next(model.parameters()).device
    parameters = sum(parameter.numel() for parameter in model.parameters())
    assistant_tokens = int(train_mask.sum().item())
    validation_assistant_tokens = int(validation_mask.sum().item())
    tokens_per_parameter = assistant_tokens / max(1, parameters)
    print(
        f"Jon2 dialogue model | parameters={parameters:,} | "
        f"train_assistant_tokens={assistant_tokens:,} | "
        f"validation_assistant_tokens={validation_assistant_tokens:,} | "
        f"train_tokens_per_parameter={tokens_per_parameter:.6f} | device={device}"
    )
    if tokens_per_parameter < args.minimum_assistant_tokens_per_parameter:
        raise ValueError(
            f"Training blocked: {tokens_per_parameter:.6f} assistant tokens/parameter; "
            f"minimum is {args.minimum_assistant_tokens_per_parameter:.2f}. "
            "Add diverse, rights-approved dialogue. Do not duplicate examples or lower this guard."
        )

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    best_validation = float("inf")
    best_state = None
    for step in range(1, args.steps + 1):
        model.train()
        x, y, mask = assistant_only_batch(
            train_data, train_mask, args.context, args.batch_size, device
        )
        logits = model(x)
        loss = masked_language_model_loss(logits, y, mask)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            validation_loss = estimate_assistant_loss(
                model, validation_data, validation_mask,
                args.context, args.batch_size, device, args.eval_steps,
            )
            print(
                f"step={step}/{args.steps} train_loss={loss.item():.4f} "
                f"assistant_validation_loss={validation_loss:.4f}"
            )
            if validation_loss < best_validation:
                best_validation = validation_loss
                best_state = {
                    key: value.detach().cpu().clone()
                    for key, value in model.state_dict().items()
                }

    if best_state is None:
        raise RuntimeError("No best checkpoint was produced.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    corpus_text = format_dialogues(conversations)
    checkpoint = {
        "model_state": best_state,
        "tokenizer": tokenizer.to_dict(),
        "config": config,
        "training_steps": args.steps,
        "best_assistant_validation_loss": best_validation,
        "dialogue_count": len(conversations),
        "assistant_training_tokens": assistant_tokens,
        "corpus_sha256": hashlib.sha256(corpus_text.encode("utf-8")).hexdigest(),
        "training_method": "assistant_only_next_token_loss_v1",
        "model_name": "Jon2 Original Transformer — Assistant Only",
        "release_approved": False,
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    torch.save(checkpoint, temporary)
    temporary.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "checkpoint": output.name,
        "sha256": digest,
        "size_bytes": output.stat().st_size,
        "release_approved": False,
        "human_review_required": True,
    }
    output.with_suffix(output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved experimental checkpoint: {output}")
    print("RELEASE_STATUS: BLOCKED_PENDING_HELD_OUT_HUMAN_REVIEW")


def main():
    parser = argparse.ArgumentParser(
        description="Train Jon2 from scratch on approved dialogues using assistant-only loss."
    )
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--approval-manifest", default="ai_engine/training_data/source_approvals.json")
    parser.add_argument("--output", default="ai_engine/checkpoints/jon2-dialogue-v1.pt")
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--context", type=int, default=128)
    parser.add_argument("--width", type=int, default=96)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=0.1)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--tokenizer-vocab-size", type=int, default=512)
    parser.add_argument("--tokenizer-min-frequency", type=int, default=2)
    parser.add_argument("--minimum-assistant-tokens-per-parameter", type=float, default=10.0)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    positive = (
        args.steps, args.batch_size, args.context, args.width, args.heads,
        args.layers, args.tokenizer_vocab_size, args.tokenizer_min_frequency,
        args.eval_every, args.eval_steps,
    )
    if min(positive) <= 0:
        parser.error("training sizes and intervals must be positive")
    if args.width % args.heads:
        parser.error("width must be divisible by heads")
    if args.minimum_assistant_tokens_per_parameter <= 0:
        parser.error("minimum-assistant-tokens-per-parameter must be positive")
    if args.weight_decay < 0 or args.learning_rate <= 0:
        parser.error("learning rate must be positive and weight decay nonnegative")
    train(args)


if __name__ == "__main__":
    main()
