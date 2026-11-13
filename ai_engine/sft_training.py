"""Safe assistant-only SFT runner for a private original Jon2 checkpoint.

This command is opt-in and is never run by import or CI. It requires an
approved private JSONL corpus and writes a new checkpoint path only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

_ENGINE_DIR = str(Path(__file__).resolve().parent)
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from jon2_core import Jon2Transformer
from sft_data import (
    IGNORE_INDEX,
    SFTConversationDataset,
    collate_sft_batch,
    load_approved_sft_splits,
)
from tokenizer import ByteBPETokenizer

MIN_SFT_CONVERSATIONS = 50
MIN_SFT_ASSISTANT_TOKENS = 10_000


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_new_output_path(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve():
        raise ValueError("SFT output must be a new path; the source checkpoint is protected.")
    if output.exists():
        raise FileExistsError(
            f"SFT output already exists: {output}. Choose a new checkpoint filename."
        )


def _load_private_checkpoint(path: Path, device: torch.device):
    if not path.is_file():
        raise FileNotFoundError(f"Private Jon2 checkpoint not found: {path}")
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint must be a Jon2 checkpoint dictionary.")
    if not isinstance(checkpoint.get("tokenizer"), dict):
        raise ValueError("Checkpoint lacks the supported Byte-BPE tokenizer; refusing conversion.")
    if not isinstance(checkpoint.get("config"), dict):
        raise ValueError("Checkpoint is missing its original model configuration.")
    if not isinstance(checkpoint.get("model_state"), dict):
        raise ValueError("Checkpoint is missing its original model weights.")

    tokenizer = ByteBPETokenizer.from_dict(checkpoint["tokenizer"])
    config = dict(checkpoint["config"])
    required = {"width", "heads", "layers", "context", "dropout"}
    if not required.issubset(config):
        raise ValueError("Checkpoint model configuration is incomplete.")
    model = Jon2Transformer(vocab_size=tokenizer.vocab_size, **config).to(device)
    model.load_state_dict(checkpoint["model_state"], strict=True)
    return checkpoint, tokenizer, model


def _supervised_token_count(examples: list[dict[str, list[int]]]) -> int:
    return sum(
        sum(label != IGNORE_INDEX for label in example["labels"])
        for example in examples
    )


def _epoch_loss(model, loader, device, optimizer=None) -> float:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_tokens = 0
    context_manager = torch.enable_grad if training else torch.inference_mode
    with context_manager():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            logits = model(input_ids)
            shifted_logits = logits[:, :-1, :].contiguous()
            shifted_labels = labels[:, 1:].contiguous()
            active_tokens = int((shifted_labels != IGNORE_INDEX).sum().item())
            if active_tokens == 0:
                continue
            loss = torch.nn.functional.cross_entropy(
                shifted_logits.view(-1, shifted_logits.size(-1)),
                shifted_labels.view(-1),
                ignore_index=IGNORE_INDEX,
            )
            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            total_loss += float(loss.item()) * active_tokens
            total_tokens += active_tokens
    if total_tokens == 0:
        raise ValueError("No assistant response tokens were available for SFT loss.")
    return total_loss / total_tokens


def train_sft(
    *,
    checkpoint_path: str | Path,
    data_dir: str | Path,
    approval_manifest: str | Path,
    output_path: str | Path,
    epochs: int = 1,
    batch_size: int = 4,
    learning_rate: float = 1e-4,
    validation_fraction: float = 0.1,
    seed: int = 42,
) -> dict:
    """Fine-tune assistant responses only and save to a never-overwritten path."""
    source = Path(checkpoint_path)
    output = Path(output_path)
    manifest_path = Path(approval_manifest)
    _validate_new_output_path(source, output)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Private approval manifest not found: {manifest_path}")
    if epochs <= 0 or batch_size <= 0 or learning_rate <= 0:
        raise ValueError("epochs, batch_size, and learning_rate must be positive.")

    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    source_hash = _sha256_file(source)
    manifest_hash = _sha256_file(manifest_path)
    checkpoint, tokenizer, model = _load_private_checkpoint(source, device)
    context = int(checkpoint["config"]["context"])
    train_examples, validation_examples = load_approved_sft_splits(
        data_dir,
        manifest_path,
        tokenizer,
        max_length=context,
        validation_fraction=validation_fraction,
        seed=seed,
    )

    train_tokens = _supervised_token_count(train_examples)
    if len(train_examples) < MIN_SFT_CONVERSATIONS or train_tokens < MIN_SFT_ASSISTANT_TOKENS:
        raise ValueError(
            "SFT blocked: approved assistant-response data is insufficient. "
            f"Training conversations={len(train_examples):,}/{MIN_SFT_CONVERSATIONS:,}; "
            f"assistant target tokens={train_tokens:,}/{MIN_SFT_ASSISTANT_TOKENS:,}. "
            "Add distinct, rights-cleared, reviewed conversations; do not duplicate data "
            "or lower the gate."
        )

    train_loader = DataLoader(
        SFTConversationDataset(train_examples),
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_sft_batch,
        generator=torch.Generator().manual_seed(seed),
    )
    validation_loader = DataLoader(
        SFTConversationDataset(validation_examples),
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_sft_batch,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    validation_loss = None
    completed_epochs = 0
    for epoch in range(1, epochs + 1):
        train_loss = _epoch_loss(model, train_loader, device, optimizer)
        validation_loss = _epoch_loss(model, validation_loader, device)
        completed_epochs = epoch
        print(
            f"SFT epoch {epoch}/{epochs} | assistant_train_loss={train_loss:.4f} "
            f"| assistant_validation_loss={validation_loss:.4f}"
        )

    # Re-check immediately before writing so an existing destination is never replaced.
    _validate_new_output_path(source, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = dict(checkpoint)
    result["model_state"] = model.cpu().state_dict()
    result["sft_metadata"] = {
        "method": "assistant_only_cross_entropy",
        "epochs": completed_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "seed": seed,
        "training_conversations": len(train_examples),
        "validation_conversations": len(validation_examples),
        "training_assistant_tokens": train_tokens,
        "validation_assistant_tokens": _supervised_token_count(validation_examples),
        "validation_loss": validation_loss,
        "source_checkpoint_sha256": source_hash,
        "approval_manifest_sha256": manifest_hash,
        "approved_sources": json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "approved_sources", []
        ),
    }
    # Keep the source checkpoint untouched; only the new output path is written.
    torch.save(result, output)
    print(f"Saved SFT checkpoint: {output.resolve()}")
    return result["sft_metadata"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Assistant-only SFT for original Jon2.")
    parser.add_argument("--checkpoint", required=True, help="Private original Jon2 .pt checkpoint.")
    parser.add_argument("--data", required=True, help="Private directory containing approved JSONL only.")
    parser.add_argument("--approval-manifest", required=True, help="Private exact-file approval JSON.")
    parser.add_argument("--output", required=True, help="New checkpoint path; existing files are never overwritten.")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train_sft(
        checkpoint_path=args.checkpoint,
        data_dir=args.data,
        approval_manifest=args.approval_manifest,
        output_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        validation_fraction=args.validation_fraction,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
