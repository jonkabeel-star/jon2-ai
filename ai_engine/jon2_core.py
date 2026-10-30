"""Jon2 AI: original, from-scratch character-level language model.

This is an original project-owned model implementation. It starts with random
weights and MUST be trained on properly licensed/owned text before use.
It does not call an external AI API or download pretrained model weights.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import torch
from torch import nn


SPECIAL_UNK = "�"


def read_corpus(folder: Path) -> str:
    files = sorted(folder.rglob("*.txt"))
    if not files:
        raise FileNotFoundError(
            f"No .txt training files found in {folder}. Add Arabic text you own "
            "or are licensed to use."
        )
    parts = []
    for path in files:
        parts.append(path.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(parts).strip()
    if len(text) < 1000:
        raise ValueError("Training corpus is too small. Add at least 1,000 characters.")
    return text


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
        batch, length = token_ids.shape
        if length > self.context:
            token_ids = token_ids[:, -self.context:]
            length = self.context
        positions = torch.arange(length, device=token_ids.device)
        hidden = self.token_embedding(token_ids) + self.position_embedding(positions)[None, :, :]
        causal_mask = torch.triu(
            torch.ones(length, length, device=token_ids.device, dtype=torch.bool),
            diagonal=1,
        )
        hidden = self.blocks(hidden, mask=causal_mask)
        return self.output(self.final_norm(hidden))


def train(args: argparse.Namespace) -> None:
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    corpus = read_corpus(Path(args.data))
    tokenizer = CharacterTokenizer.from_text(corpus)
    encoded = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    if len(encoded) <= args.context + 1:
        raise ValueError("Training text must be longer than context + 1 characters.")

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

    print(f"Jon2 original model | device={device} | chars={len(encoded)}")
    print(f"Vocabulary={len(tokenizer.vocabulary)} | parameters={sum(p.numel() for p in model.parameters()):,}")

    for step in range(1, args.steps + 1):
        starts = torch.randint(0, len(encoded) - args.context - 1, (args.batch_size,))
        x = torch.stack([encoded[i:i + args.context] for i in starts]).to(device)
        y = torch.stack([encoded[i + 1:i + args.context + 1] for i in starts]).to(device)
        logits = model(x)
        loss = nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % args.log_every == 0:
            print(f"step {step}/{args.steps} | loss={loss.item():.4f}")

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
        },
        output,
    )
    print(f"Saved trained Jon2 model to: {output}")


def load_model(checkpoint_path: str, device: str | None = None):
    target = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint = torch.load(checkpoint_path, map_location=target, weights_only=False)
    tokenizer = CharacterTokenizer(checkpoint["vocabulary"])
    model = Jon2Transformer(
        vocab_size=len(tokenizer.vocabulary),
        **checkpoint["config"],
    ).to(target)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, tokenizer, target


@torch.inference_mode()
def generate(model, tokenizer, prompt: str, device, max_new_chars: int = 400, temperature: float = 0.8):
    if not prompt.strip():
        raise ValueError("اكتب رسالة أولًا.")
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
    parser = argparse.ArgumentParser(description="Train the original Jon2 AI language model.")
    parser.add_argument("--data", default="training_data", help="Folder containing licensed .txt files")
    parser.add_argument("--output", default="checkpoints/jon2-small.pt")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--context", type=int, default=128)
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if min(args.steps, args.batch_size, args.context, args.width, args.heads, args.layers) <= 0:
        parser.error("training dimensions and steps must be positive")
    train(args)


if __name__ == "__main__":
    main()
