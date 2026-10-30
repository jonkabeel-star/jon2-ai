"""Original Jon2 AI character-level Transformer and training pipeline.

Weights start random. No pretrained model, external AI API, or third-party
model checkpoint is loaded. Train only on project-owned or explicitly licensed
text. This small architecture is an educational prototype, not a ChatGPT-scale model.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import torch
from torch import nn

from tokenizer import ByteBPETokenizer

SPECIAL_UNK = "�"


def read_corpus(folder: Path) -> str:
    files = sorted(folder.rglob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt training files found in {folder}.")
    parts = []
    for path in files:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        # Ignore metadata/comment lines while keeping the authored text.
        useful = [line for line in lines if not line.lstrip().startswith("#")]
        text = "\n".join(useful).strip()
        if text:
            parts.append(text)
    corpus = "\n\n".join(parts).strip()
    if len(corpus) < 1000:
        raise ValueError(
            f"Corpus has only {len(corpus)} characters. Add more original or "
            "properly licensed training text before training."
        )
    return corpus


class CharacterTokenizer:
    def __init__(self, vocabulary: list[str]):
        self.vocabulary = vocabulary
        self.to_id = {char: index for index, char in enumerate(vocabulary)}
        self.unk_id = self.to_id.get(SPECIAL_UNK, 0)

    @classmethod
    def from_text(cls, text: str) -> "CharacterTokenizer":
        chars = sorted(set(text))
        if SPECIAL_UNK not in chars:
            chars.insert(0, SPECIAL_UNK)
        return cls(chars)

    def encode(self, text: str) -> list[int]:
        return [self.to_id.get(char, self.unk_id) for char in text]

    def decode(self, ids: list[int]) -> str:
        return "".join(self.vocabulary[index] for index in ids)


class Jon2Transformer(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        width: int = 128,
        heads: int = 4,
        layers: int = 4,
        context: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        if width % heads:
            raise ValueError("width must be divisible by heads")
        self.context = context
        self.token_embedding = nn.Embedding(vocab_size, width)
        self.position_embedding = nn.Embedding(context, width)
        block = nn.TransformerEncoderLayer(
            d_model=width,
            nhead=heads,
            dim_feedforward=4 * width,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
            activation="gelu",
        )
        self.blocks = nn.TransformerEncoder(block, num_layers=layers)
        self.final_norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, vocab_size, bias=False)
        self.output.weight = self.token_embedding.weight

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        _, length = token_ids.shape
        if length > self.context:
            token_ids = token_ids[:, -self.context:]
            length = self.context
        positions = torch.arange(length, device=token_ids.device)
        hidden = self.token_embedding(token_ids)
        hidden = hidden + self.position_embedding(positions)[None, :, :]
        causal_mask = torch.triu(
            torch.ones(length, length, device=token_ids.device, dtype=torch.bool),
            diagonal=1,
        )
        hidden = self.blocks(hidden, mask=causal_mask)
        return self.output(self.final_norm(hidden))


def _batch(data: torch.Tensor, context: int, batch_size: int, device):
    starts = torch.randint(0, len(data) - context - 1, (batch_size,))
    x = torch.stack([data[i:i + context] for i in starts]).to(device)
    y = torch.stack([data[i + 1:i + context + 1] for i in starts]).to(device)
    return x, y


@torch.inference_mode()
def _estimate_loss(model, train_data, val_data, context, batch_size, device, eval_steps):
    model.eval()
    scores = {}
    for name, data in (("train", train_data), ("validation", val_data)):
        losses = []
        for _ in range(eval_steps):
            x, y = _batch(data, context, batch_size, device)
            logits = model(x)
            loss = nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)), y.reshape(-1)
            )
            losses.append(float(loss.item()))
        scores[name] = sum(losses) / len(losses)
    model.train()
    return scores


def train(args: argparse.Namespace) -> None:
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    corpus = read_corpus(Path(args.data))
    tokenizer = CharacterTokenizer.from_text(corpus)
    encoded = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    if len(encoded) <= args.context * 2 + 2:
        raise ValueError("Training text must be longer than twice the context window.")
    split_at = int(len(encoded) * (1.0 - args.validation_fraction))
    train_data = encoded[:split_at]
    val_data = encoded[split_at:]
    if len(val_data) <= args.context + 1:
        raise ValueError("Validation text is too short; add more training text.")

    model = Jon2Transformer(
        vocab_size=len(tokenizer.vocabulary),
        width=args.width,
        heads=args.heads,
        layers=args.layers,
        context=args.context,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()

    parameter_count = sum(p.numel() for p in model.parameters())
    print(f"Jon2 original model | device={device} | corpus_chars={len(encoded)}")
    print(f"train_chars={len(train_data)} | validation_chars={len(val_data)}")
    print(f"vocabulary={len(tokenizer.vocabulary)} | parameters={parameter_count:,}")
    if len(encoded) < 100_000:
        print("WARNING: corpus is still small; expect weak text generation, not general intelligence.")

    for step in range(1, args.steps + 1):
        x, y = _batch(train_data, args.context, args.batch_size, device)
        logits = model(x)
        loss = nn.functional.cross_entropy(
            logits.reshape(-1, logits.size(-1)), y.reshape(-1)
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step == 1 or step % args.log_every == 0 or step == args.steps:
            scores = _estimate_loss(
                model, train_data, val_data, args.context, args.batch_size,
                device, args.eval_steps,
            )
            print(
                f"step {step}/{args.steps} | "
                f"train_loss={scores['train']:.4f} | "
                f"validation_loss={scores['validation']:.4f}"
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "width": args.width,
        "heads": args.heads,
        "layers": args.layers,
        "context": args.context,
        "dropout": args.dropout,
    }
    torch.save(
        {
            "model_state": model.cpu().state_dict(),
            "vocabulary": tokenizer.vocabulary,
            "config": config,
            "training_steps": args.steps,
            "corpus_characters": len(encoded),
            "validation_fraction": args.validation_fraction,
            "model_name": "Jon2 Original Transformer",
        },
        output,
    )
    print(f"Saved Jon2 checkpoint: {output.resolve()}")


def load_model(checkpoint_path: str, device: str | None = None):
    target = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint = torch.load(
        checkpoint_path, map_location=target, weights_only=False
    )
    if "tokenizer" in checkpoint:
        tokenizer = ByteBPETokenizer.from_dict(checkpoint["tokenizer"])
        vocab_size = tokenizer.vocab_size
    else:
        tokenizer = CharacterTokenizer(checkpoint["vocabulary"])
        vocab_size = len(tokenizer.vocabulary)
    model = Jon2Transformer(
        vocab_size=vocab_size,
        **checkpoint["config"],
    ).to(target)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, tokenizer, target


@torch.inference_mode()
def generate(
    model, tokenizer, prompt: str, device,
    max_new_chars: int = 400, temperature: float = 0.8,
):
    if not prompt.strip():
        raise ValueError("اكتب رسالتك أولًا.")
    if temperature <= 0:
        raise ValueError("temperature must be greater than zero")
    ids = tokenizer.encode(prompt)
    if not ids:
        ids = [tokenizer.unk_id]
    tokens = torch.tensor([ids], dtype=torch.long, device=device)
    for _ in range(max_new_chars):
        context = tokens[:, -model.context:]
        logits = model(context)[:, -1, :] / temperature
        probabilities = torch.softmax(logits, dim=-1)
        next_id = torch.multinomial(probabilities, num_samples=1)
        tokens = torch.cat((tokens, next_id), dim=1)
    return tokenizer.decode(tokens[0].tolist())


def main():
    parser = argparse.ArgumentParser(
        description="Train the original Jon2 AI language model."
    )
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--output", default="ai_engine/checkpoints/jon2-small.pt")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--context", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--eval-steps", type=int, default=10)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if min(
        args.steps, args.batch_size, args.context, args.width,
        args.heads, args.layers, args.eval_steps, args.log_every,
    ) <= 0:
        parser.error("training dimensions and steps must be positive")
    if not 0.05 <= args.validation_fraction <= 0.4:
        parser.error("validation-fraction must be between 0.05 and 0.4")
    train(args)


if __name__ == "__main__":
    main()
