"""Assistant-only supervised objective for the original Jon2 Transformer.

User turns are retained as context, but loss is applied only to assistant
response tokens. This is an optional from-scratch training path; it never
downloads pretrained weights or calls a hosted AI API.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import torch
from torch.nn import functional as F


def load_dialogue_records(data_dir: str | Path) -> list[list[dict[str, str]]]:
    """Load structured JSONL conversations. Caller must validate source approvals first."""
    root = Path(data_dir)
    files = sorted(path for path in root.rglob("*.jsonl") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No JSONL dialogue files found in {root}.")
    conversations: list[list[dict[str, str]]] = []
    for path in files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path.name}:{line_no}: {exc.msg}") from exc
            messages = record.get("messages") if isinstance(record, dict) else None
            if not isinstance(messages, list) or not messages:
                raise ValueError(f"{path.name}:{line_no}: messages must be a non-empty list.")
            normalized = []
            seen_roles = set()
            previous_role = None
            for message in messages:
                if not isinstance(message, dict):
                    raise ValueError(f"{path.name}:{line_no}: each message must be an object.")
                role, content = message.get("role"), message.get("content")
                if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                    raise ValueError(f"{path.name}:{line_no}: use non-empty user/assistant messages.")
                if role == previous_role:
                    raise ValueError(f"{path.name}:{line_no}: turns must alternate user and assistant.")
                normalized.append({"role": role, "content": content.strip()})
                seen_roles.add(role)
                previous_role = role
            if not {"user", "assistant"}.issubset(seen_roles):
                raise ValueError(f"{path.name}:{line_no}: conversation needs user and assistant turns.")
            if normalized[0]["role"] != "user" or normalized[-1]["role"] != "assistant":
                raise ValueError(f"{path.name}:{line_no}: conversation must start with user and end with assistant.")
            conversations.append(normalized)
    if len(conversations) < 2:
        raise ValueError("At least two approved dialogue conversations are required.")
    return conversations


def split_dialogues(conversations, validation_fraction: float = 0.1, seed: int = 42):
    """Deterministically split whole conversations to prevent turn leakage."""
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("validation_fraction must be between 0.05 and 0.4.")
    if len(conversations) < 2:
        raise ValueError("At least two conversations are required for a held-out split.")
    indices = list(range(len(conversations)))
    random.Random(seed).shuffle(indices)
    validation_count = max(1, round(len(indices) * validation_fraction))
    validation_ids = set(indices[:validation_count])
    train = [item for i, item in enumerate(conversations) if i not in validation_ids]
    validation = [item for i, item in enumerate(conversations) if i in validation_ids]
    return train, validation


def format_dialogues(conversations) -> str:
    """Return readable dialogue text for fitting the tokenizer on training only."""
    blocks = []
    for conversation in conversations:
        turns = []
        for message in conversation:
            label = "المستخدم" if message["role"] == "user" else "Jon2"
            turns.append(f"{label}: {message['content']}")
        blocks.append("\n".join(turns))
    return "\n\n".join(blocks)


def encode_assistant_only(conversations, tokenizer):
    """Encode complete turns and mark only assistant content as prediction targets."""
    token_ids: list[int] = []
    loss_mask: list[bool] = []
    for conversation in conversations:
        for message in conversation:
            label = "المستخدم" if message["role"] == "user" else "Jon2"
            prefix_ids = tokenizer.encode(f"{label}: ")
            content_ids = tokenizer.encode(message["content"])
            newline_ids = tokenizer.encode("\n")
            token_ids.extend(prefix_ids)
            loss_mask.extend([False] * len(prefix_ids))
            token_ids.extend(content_ids)
            loss_mask.extend([message["role"] == "assistant"] * len(content_ids))
            token_ids.extend(newline_ids)
            loss_mask.extend([False] * len(newline_ids))
        separator_ids = tokenizer.encode("\n")
        token_ids.extend(separator_ids)
        loss_mask.extend([False] * len(separator_ids))
    if not token_ids or len(token_ids) != len(loss_mask):
        raise ValueError("Dialogue tokenization produced an invalid token/mask stream.")
    return torch.tensor(token_ids, dtype=torch.long), torch.tensor(loss_mask, dtype=torch.bool)


def assistant_only_batch(data, loss_mask, context: int, batch_size: int, device):
    """Sample windows guaranteed to contain at least one assistant target."""
    if context <= 0 or batch_size <= 0:
        raise ValueError("context and batch_size must be positive.")
    if data.ndim != 1 or loss_mask.ndim != 1 or len(data) != len(loss_mask):
        raise ValueError("data and loss_mask must be equal-length one-dimensional tensors.")
    if len(data) <= context + 1:
        raise ValueError("training data must be longer than context + 1.")
    target_positions = torch.nonzero(loss_mask[1:], as_tuple=False).flatten() + 1
    if target_positions.numel() == 0:
        raise ValueError("No assistant response tokens are available for training.")
    selected = target_positions[
        torch.randint(0, target_positions.numel(), (batch_size,), device=target_positions.device)
    ]
    max_start = len(data) - context - 1
    starts = []
    for target in selected.tolist():
        low = max(0, target - context)
        high = min(target, max_start)
        starts.append(random.randint(low, high))
    starts = torch.tensor(starts, dtype=torch.long, device=data.device)
    offsets = torch.arange(context, device=data.device)
    indices = starts[:, None] + offsets[None, :]
    x = data[indices].to(device, non_blocking=True)
    y = data[indices + 1].to(device, non_blocking=True)
    mask = loss_mask[indices + 1].to(device, non_blocking=True)
    if not mask.any(dim=1).all():
        raise RuntimeError("Internal sampler error: a batch row has no assistant target.")
    return x, y, mask


def masked_language_model_loss(logits, targets, loss_mask):
    """Cross-entropy over assistant response tokens only."""
    if logits.shape[:2] != targets.shape or targets.shape != loss_mask.shape:
        raise ValueError("logits, targets, and loss_mask shapes do not align.")
    active = loss_mask.reshape(-1).bool()
    if not active.any():
        raise ValueError("Cannot calculate assistant-only loss with an empty target mask.")
    per_token = F.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        targets.reshape(-1),
        reduction="none",
    )
    return per_token[active].mean()


@torch.inference_mode()
def estimate_assistant_loss(model, data, loss_mask, context, batch_size, device, eval_steps):
    """Estimate validation loss only on held-out assistant response tokens."""
    model.eval()
    losses = []
    for _ in range(eval_steps):
        x, y, mask = assistant_only_batch(data, loss_mask, context, batch_size, device)
        losses.append(float(masked_language_model_loss(model(x), y, mask).item()))
    model.train()
    return sum(losses) / len(losses)
