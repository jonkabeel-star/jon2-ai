"""Conversation validation and context-window preparation for original Jon2.

This module preserves the current user turn and removes only the oldest complete
history turns when a prompt exceeds the model context. It never truncates the
current question or fabricates conversation content.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class Encoder(Protocol):
    def encode(self, text: str) -> list[int]: ...


def validate_messages(messages: object, *, require_complete: bool = True) -> list[dict[str, str]]:
    """Validate a strict user/assistant alternating conversation."""
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    normalized: list[dict[str, str]] = []
    expected_role = "user"
    for index, item in enumerate(messages):
        if not isinstance(item, dict):
            raise ValueError(f"message {index + 1} must be an object")
        role, content = item.get("role"), item.get("content")
        if role not in {"user", "assistant"}:
            raise ValueError(f"message {index + 1} has an unsupported role")
        if role != expected_role:
            raise ValueError(
                f"message {index + 1} must have role {expected_role!r}, got {role!r}"
            )
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"message {index + 1} content must be a non-empty string")
        normalized.append({"role": role, "content": content.strip()})
        expected_role = "assistant" if role == "user" else "user"
    if require_complete and normalized[-1]["role"] != "assistant":
        raise ValueError("training conversation must end with an assistant message")
    if not require_complete and normalized[-1]["role"] != "user":
        raise ValueError("inference history must end with the current user message")
    return normalized


def load_conversations(path: Path) -> list[list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Conversation dataset not found: {path}")
    conversations = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
        if not isinstance(record, dict) or "messages" not in record:
            raise ValueError(f"Line {line_number} must contain a messages field")
        try:
            conversations.append(validate_messages(record["messages"]))
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: {exc}") from exc
    if not conversations:
        raise ValueError("Conversation dataset is empty")
    return conversations


def audit_conversations(conversations: list[list[dict[str, str]]]) -> dict:
    """Report conversation depth and duplicates without scoring semantic quality."""
    if not conversations:
        raise ValueError("At least one conversation is required")
    canonical = [
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in conversations
    ]
    unique = len(set(canonical))
    multi_turn = sum(1 for item in conversations if len(item) >= 4)
    message_count = sum(len(item) for item in conversations)
    assistant_tokens = sum(
        len(message["content"].split())
        for conversation in conversations
        for message in conversation
        if message["role"] == "assistant"
    )
    return {
        "conversation_count": len(conversations),
        "unique_conversation_count": unique,
        "duplicate_conversation_count": len(conversations) - unique,
        "message_count": message_count,
        "multi_turn_conversation_count": multi_turn,
        "single_exchange_conversation_count": len(conversations) - multi_turn,
        "assistant_word_count_approx": assistant_tokens,
        "multi_turn_fraction": round(multi_turn / len(conversations), 6),
        "semantic_quality_assessed": False,
        "human_review_required": True,
    }


def format_context(messages: object, tokenizer: Encoder, max_context_tokens: int) -> tuple[str, int]:
    """Format history while preserving the current question and whole turns."""
    if max_context_tokens <= 0:
        raise ValueError("max_context_tokens must be positive")
    turns = validate_messages(messages, require_complete=False)
    def render(items: list[dict[str, str]]) -> str:
        return "".join(
            ("المستخدم: " if item["role"] == "user" else "Jon2: ")
            + item["content"] + "\n"
            for item in items
        ) + "Jon2:"
    # Drop the oldest user/assistant pair only; never shorten the current question.
    candidate = list(turns)
    prompt = render(candidate)
    token_count = len(tokenizer.encode(prompt))
    while token_count > max_context_tokens and len(candidate) > 1:
        if len(candidate) < 3:
            break
        candidate = candidate[2:]
        prompt = render(candidate)
        token_count = len(tokenizer.encode(prompt))
    if token_count > max_context_tokens:
        raise ValueError(
            "The current user question does not fit the model context; "
            "it was preserved and no generation should be attempted."
        )
    return prompt, len(turns) - len(candidate)
