"""Bounded, turn-aware conversation context for Jon2.

This module does not invent or summarize user facts. It preserves the newest
complete turns that fit the model's measured prompt-token budget and reports
when older context had to be dropped.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

ALLOWED_ROLES = frozenset({"user", "assistant"})
DEFAULT_MAX_HISTORY_MESSAGES = 40
MAX_MESSAGE_CHARS = 2000


class ConversationContextError(ValueError):
    """Raised when the current request cannot fit without losing its content."""


def normalize_history(
    history: Iterable[Mapping[str, Any]] | None,
    *,
    max_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
    max_message_chars: int = MAX_MESSAGE_CHARS,
) -> list[dict[str, str]]:
    """Validate client-supplied turns; never accept client-provided system roles."""
    if history is None:
        return []
    if isinstance(history, (str, bytes)):
        raise ValueError("history must be a list of messages")

    normalized: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, Mapping):
            raise ValueError("each history item must be an object")
        role = item.get("role")
        content = item.get("content")
        if role not in ALLOWED_ROLES:
            raise ValueError("history role must be user or assistant")
        if not isinstance(content, str):
            raise ValueError("history content must be text")
        content = content.strip()
        if not content:
            continue
        if len(content) > max_message_chars:
            raise ValueError("history message exceeds the character limit")
        normalized.append({"role": role, "content": content})

    if len(normalized) > max_messages:
        normalized = normalized[-max_messages:]
    return normalized


def _drop_oldest_turn(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop one oldest user turn and its first assistant response when present."""
    if not history:
        return history
    if history[0]["role"] != "user":
        return history[1:]

    assistant_index = next(
        (index for index, item in enumerate(history[1:], start=1)
         if item["role"] == "assistant"),
        None,
    )
    if assistant_index is None:
        return history[1:]
    return history[assistant_index + 1:]


def build_context_messages(
    *,
    system_prompt: str,
    history: Iterable[Mapping[str, Any]] | None,
    current_message: str,
    count_tokens: Callable[[list[dict[str, str]]], int],
    max_input_tokens: int,
    max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
) -> tuple[list[dict[str, str]], dict[str, int | bool]]:
    """Build a complete prompt while preserving the current request and newest turns.

    count_tokens must measure the exact chat-template tokenization used by the
    model. Old turns are removed only as whole user/assistant turns where possible.
    The current message and system prompt are never silently truncated.
    """
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt is required")
    if not isinstance(current_message, str) or not current_message.strip():
        raise ValueError("current_message is required")
    if not isinstance(max_input_tokens, int) or isinstance(max_input_tokens, bool) or max_input_tokens < 1:
        raise ValueError("max_input_tokens must be a positive integer")

    turns = normalize_history(history, max_messages=max_history_messages)
    messages = [{"role": "system", "content": system_prompt.strip()}, *turns,
                {"role": "user", "content": current_message.strip()}]
    original_history_count = len(turns)

    token_count = int(count_tokens(messages))
    if token_count < 0:
        raise ValueError("count_tokens returned a negative value")

    while token_count > max_input_tokens and turns:
        turns = _drop_oldest_turn(turns)
        messages = [{"role": "system", "content": system_prompt.strip()}, *turns,
                    {"role": "user", "content": current_message.strip()}]
        token_count = int(count_tokens(messages))

    if token_count > max_input_tokens:
        raise ConversationContextError(
            "system prompt and current message exceed the configured input-token budget"
        )

    return messages, {
        "input_tokens": token_count,
        "history_messages_used": len(turns),
        "history_messages_dropped": original_history_count - len(turns),
        "context_truncated": len(turns) != original_history_count,
    }
