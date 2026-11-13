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
from source_approval import validate_source_approvals

SPECIAL_UNK = "�"


from corpus_reader import read_corpus
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
    """Sample next-token windows with vectorized indexing (no Python slice loop)."""
    if context <= 0 or batch_size <= 0:
        raise ValueError("context and batch_size must be positive")
    if data.ndim != 1 or len(data) <= context + 1:
        raise ValueError("training data must be a 1D tensor longer than context + 1")

    # Keep sampling/indexing beside the source tensor, then transfer only the
    # completed mini-batch to the compute device.
    starts = torch.randint(
        0, len(data) - context - 1, (batch_size,), device=data.device
    )
    offsets = torch.arange(context, device=data.device)
    indices = starts[:, None] + offsets[None, :]
    x = data[indices].to(device, non_blocking=True)
    y = data[indices + 1].to(device, non_blocking=True)
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
    validate_source_approvals(Path(args.data), Path(args.approval_manifest))
    corpus = read_corpus(Path(args.data))
    if len(corpus) < args.minimum_chars:
        raise ValueError(
            f"Training corpus has {len(corpus):,} characters; this run requires "
            f"at least {args.minimum_chars:,}. Add reviewed, project-owned or "
            "properly licensed data. Do not duplicate text to pass this check."
        )
    resume_checkpoint = None
    resume_sha256 = None
    previous_training_steps = 0
    if args.resume_from:
        resume_path = Path(args.resume_from)
        if not resume_path.is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {resume_path}")
        if Path(args.output).resolve() == resume_path.resolve():
            raise ValueError(
                "Output checkpoint must be a new path; the original resume checkpoint is protected."
            )
        import hashlib
        resume_sha256 = hashlib.sha256(resume_path.read_bytes()).hexdigest()
        resume_checkpoint = torch.load(
            resume_path, map_location=device, weights_only=True
        )
        if not isinstance(resume_checkpoint, dict):
            raise ValueError("Resume checkpoint must be a Jon2 checkpoint dictionary.")
        if not isinstance(resume_checkpoint.get("tokenizer"), dict):
            raise ValueError(
                "This checkpoint does not contain the supported Byte-BPE tokenizer; "
                "refusing to change token IDs during resume."
            )
        if not isinstance(resume_checkpoint.get("config"), dict):
            raise ValueError("Resume checkpoint is missing its model configuration.")
        tokenizer = ByteBPETokenizer.from_dict(resume_checkpoint["tokenizer"])
        model_config = dict(resume_checkpoint["config"])
        required_config = {"width", "heads", "layers", "context", "dropout"}
        if not required_config.issubset(model_config):
            raise ValueError("Resume checkpoint has an incomplete model configuration.")
        previous_training_steps = int(resume_checkpoint.get("training_steps", 0))
    else:
        tokenizer = ByteBPETokenizer.train(
            corpus,
            vocab_size=args.tokenizer_vocab_size,
            min_frequency=args.tokenizer_min_frequency,
        )
        model_config = {
            "width": args.width,
            "heads": args.heads,
            "layers": args.layers,
            "context": args.context,
            "dropout": args.dropout,
        }

    encoded = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    context = int(model_config["context"])
    if len(encoded) <= context * 2 + 2:
        raise ValueError("Training text must be longer than twice the model context window.")
    split_at = int(len(encoded) * (1.0 - args.validation_fraction))
    train_data = encoded[:split_at]
    val_data = encoded[split_at:]
    if len(val_data) <= context + 1:
        raise ValueError("Validation text is too short; add more training text.")

    model = Jon2Transformer(
        vocab_size=tokenizer.vocab_size,
        **model_config,
    ).to(device)
    if resume_checkpoint is not None:
        model.load_state_dict(resume_checkpoint["model_state"], strict=True)

    parameter_count = sum(p.numel() for p in model.parameters())
    training_tokens_per_parameter = len(train_data) / max(parameter_count, 1)
    required_training_tokens = int(parameter_count * args.minimum_tokens_per_parameter)
    required_corpus_tokens = int(
        required_training_tokens / (1.0 - args.validation_fraction)
    )
    print(f"Jon2 original model | device={device} | corpus_tokens={len(encoded):,}")
    print(f"train_tokens={len(train_data):,} | validation_tokens={len(val_data):,}")
    print(
        f"vocabulary={tokenizer.vocab_size:,} | parameters={parameter_count:,} | "
        f"training_tokens_per_parameter={training_tokens_per_parameter:.4f}"
    )
    print(
        f"Data readiness: {len(train_data):,}/{required_training_tokens:,} training tokens "
        f"({args.minimum_tokens_per_parameter:g} tokens per parameter required)."
    )
    if training_tokens_per_parameter < args.minimum_tokens_per_parameter:
        missing_tokens = max(0, required_corpus_tokens - len(encoded))
        raise ValueError(
            "Training blocked: the approved corpus is too small for this model. "
            f"Current ratio={training_tokens_per_parameter:.4f} training tokens/parameter; "
            f"required={args.minimum_tokens_per_parameter:g}; "
            f"add at least {missing_tokens:,} distinct, rights-cleared corpus tokens. "
            "Do not duplicate text or lower the quality gate."
        )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()

    for step in range(1, args.steps + 1):
        x, y = _batch(train_data, context, args.batch_size, device)
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
                model, train_data, val_data, context, args.batch_size,
                device, args.eval_steps,
            )
            print(
                f"step {step}/{args.steps} | "
                f"train_loss={scores['train']:.4f} | "
                f"validation_loss={scores['validation']:.4f}"
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    config = dict(model_config)
    torch.save(
        {
            "model_state": model.cpu().state_dict(),
            "tokenizer": tokenizer.to_dict(),
            "config": config,
            "training_steps": previous_training_steps + args.steps,
            "additional_training_steps": args.steps,
            "corpus_tokens": len(encoded),
            "corpus_characters": len(corpus),
            "training_tokens_per_parameter": training_tokens_per_parameter,
            "minimum_tokens_per_parameter": args.minimum_tokens_per_parameter,
            "resumed_from_sha256": resume_sha256,
            "validation_fraction": args.validation_fraction,
            "model_name": "Jon2 Original Transformer",
        },
        output,
    )
    print(f"Saved Jon2 checkpoint: {output.resolve()}")


def load_model(checkpoint_path: str, device: str | None = None):
    target = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint = torch.load(
        checkpoint_path, map_location=target, weights_only=True
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
    stop_sequences: list[str] | None = None,
    min_new_tokens: int = 24,
    do_sample: bool = True,
    repetition_penalty: float = 1.12,
    no_repeat_ngram_size: int = 3,
    top_k: int = 40,
):
    if not prompt.strip():
        raise ValueError("اكتب رسالتك أولًا.")
    if temperature <= 0:
        raise ValueError("temperature must be greater than zero")
    if repetition_penalty < 1.0 or no_repeat_ngram_size < 0 or top_k < 0:
        raise ValueError("Invalid repetition or top-k generation setting")
    ids = tokenizer.encode(prompt)
    if not ids:
        ids = [tokenizer.unk_id]
    stop_texts = [sequence for sequence in (stop_sequences or []) if sequence]
    stop_bytes = [(marker, marker.encode("utf-8")) for marker in stop_texts]
    matched_stop_text = None
    generated_ids = list(ids)
    prompt_token_count = len(generated_ids)
    tokens = torch.tensor([generated_ids], dtype=torch.long, device=device)
    # Byte-BPE can otherwise emit an invalid UTF-8 continuation byte.
    # Keep only candidates that preserve a valid (possibly incomplete) UTF-8 prefix.
    import codecs
    # Resolve token byte pieces once. The tokenizer also memoizes these values,
    # so candidate validation avoids repeated recursive BPE expansion.
    token_bytes = [tokenizer._token_bytes(token_id) for token_id in range(tokenizer.vocab_size)]
    generated_bytes = bytearray(b"".join(token_bytes[token_id] for token_id in ids))
    # Keep the UTF-8 decoder state at the end of the current stream. Testing a
    # candidate from this state is O(candidate_piece), not O(full_answer_length).
    utf8_decoder = codecs.getincrementaldecoder("utf-8")("strict")
    utf8_decoder.decode(bytes(generated_bytes), final=False)
    utf8_state = utf8_decoder.getstate()
    prompt_bytes = b"".join(token_bytes[token_id] for token_id in ids)
    for _ in range(max_new_chars):
        context = tokens[:, -model.context:]
        logits = model(context)[:, -1, :] / temperature
        candidate_logits = logits.clone()
        # Discourage token loops without changing the prompt's influence.
        if repetition_penalty > 1.0:
            for token_id in set(generated_ids[prompt_token_count:]):
                value = candidate_logits[0, token_id]
                candidate_logits[0, token_id] = (
                    value / repetition_penalty if value >= 0
                    else value * repetition_penalty
                )
        # Block a token that would repeat an n-gram already generated.
        if no_repeat_ngram_size > 0 and len(generated_ids) >= no_repeat_ngram_size - 1:
            prefix = generated_ids[-(no_repeat_ngram_size - 1):] if no_repeat_ngram_size > 1 else []
            banned = set()
            for index in range(len(generated_ids) - no_repeat_ngram_size + 1):
                prior = generated_ids[index:index + no_repeat_ngram_size - 1]
                if prior == prefix:
                    banned.add(generated_ids[index + no_repeat_ngram_size - 1])
            if banned:
                candidate_logits[0, list(banned)] = float("-inf")
        # First remove tokens that would corrupt the UTF-8 byte stream.
        valid_candidates = []
        for candidate, piece in enumerate(token_bytes):
            if not torch.isfinite(candidate_logits[0, candidate]):
                continue
            try:
                decoder = codecs.getincrementaldecoder("utf-8")("strict")
                decoder.setstate(utf8_state)
                decoder.decode(piece, final=False)
                valid_candidates.append(candidate)
            except UnicodeDecodeError:
                candidate_logits[0, candidate] = float("-inf")
        if not valid_candidates:
            break

        # Apply top-k only after UTF-8 filtering. Applying it before filtering
        # can leave every remaining logit at -inf and make softmax return NaN.
        if do_sample and top_k > 0 and len(valid_candidates) > top_k:
            valid_logits = candidate_logits[0, valid_candidates]
            selected_positions = torch.topk(valid_logits, top_k).indices.tolist()
            selected_candidates = [valid_candidates[index] for index in selected_positions]
            filtered_logits = torch.full_like(candidate_logits, float("-inf"))
            filtered_logits[0, selected_candidates] = candidate_logits[0, selected_candidates]
            candidate_logits = filtered_logits

        if do_sample:
            probabilities = torch.softmax(candidate_logits, dim=-1)
            if not torch.isfinite(probabilities).all() or probabilities.sum() <= 0:
                next_id = torch.argmax(candidate_logits, dim=-1, keepdim=True)
            else:
                next_id = torch.multinomial(probabilities, num_samples=1)
        else:
            next_id = torch.argmax(candidate_logits, dim=-1, keepdim=True)
        token_id = int(next_id.item())
        generated_ids.append(token_id)
        selected_piece = token_bytes[token_id]
        generated_bytes.extend(selected_piece)
        utf8_decoder = codecs.getincrementaldecoder("utf-8")("strict")
        utf8_decoder.setstate(utf8_state)
        utf8_decoder.decode(selected_piece, final=False)
        utf8_state = utf8_decoder.getstate()
        tokens = torch.cat((tokens, next_id), dim=1)

        # Match stop markers against decoded text, not separately tokenized IDs:
        # byte-BPE merges can cross the answer/marker boundary.
        # Search the generated byte stream for a complete stop marker.
        # A marker may begin inside a pre-tokenized word, so checking only
        # the decoded suffix can miss boundaries after tokenizer segmentation.
        matched_pair = next(
            (
                (marker, marker_bytes, marker_start)
                for marker, marker_bytes in stop_bytes
                if (marker_start := generated_bytes.find(marker_bytes, len(prompt_bytes))) >= 0
            ),
            None,
        )
        if matched_pair is not None:
            matched_stop_text, marker_bytes, marker_start = matched_pair
            del generated_bytes[marker_start:]
            while len(generated_ids) > prompt_token_count:
                current = b"".join(
                    token_bytes[token_id]
                    for token_id in generated_ids[prompt_token_count:]
                )
                if len(current) <= marker_start - len(prompt_bytes):
                    break
                generated_ids.pop()
            break
    # If the generation budget ends halfway through a multibyte character,
    # discard the incomplete trailing token(s) rather than decoding with U+FFFD.
    while len(generated_ids) > prompt_token_count:
        try:
            # Validate the complete prompt + continuation. A continuation token
            # may begin with UTF-8 continuation bytes that are valid only when
            # combined with the final bytes of the prompt.
            bytes(generated_bytes).decode("utf-8", errors="strict")
            break
        except UnicodeDecodeError:
            removed_id = generated_ids.pop()
            removed_piece = token_bytes[removed_id]
            if removed_piece:
                del generated_bytes[-len(removed_piece):]
    # Decode the exact byte stream so a stop marker that begins inside a
    # merged BPE token can be removed without discarding preceding answer bytes.
    decoded = bytes(generated_bytes).decode("utf-8", errors="strict")
    if matched_stop_text and decoded.endswith(matched_stop_text):
        decoded = decoded[:-len(matched_stop_text)]
    return decoded


def main():
    parser = argparse.ArgumentParser(
        description="Train the original Jon2 AI language model."
    )
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--approval-manifest", default="ai_engine/training_data/source_approvals.json")
    parser.add_argument("--minimum-chars", type=int, default=100_000)
    parser.add_argument("--tokenizer-vocab-size", type=int, default=1000)
    parser.add_argument("--tokenizer-min-frequency", type=int, default=2)
    parser.add_argument(
        "--minimum-tokens-per-parameter", type=float, default=10.0,
        help="Block training unless the approved corpus reaches this token/parameter ratio.",
    )
    parser.add_argument(
        "--resume-from", default=None,
        help="Continue from a private Jon2 checkpoint without retraining or changing its tokenizer.",
    )
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
        args.minimum_chars, args.tokenizer_vocab_size,
        args.tokenizer_min_frequency,
    ) <= 0 or args.minimum_tokens_per_parameter <= 0:
        parser.error("training dimensions and steps must be positive")
    if not 0.05 <= args.validation_fraction <= 0.4:
        parser.error("validation-fraction must be between 0.05 and 0.4")
    train(args)


if __name__ == "__main__":
    main()
