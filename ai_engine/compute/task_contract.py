"""Closed-by-default task contract for a future Jon2 Compute scheduler.

This module validates task metadata and lifecycle transitions only. It does not
queue, dispatch, execute, or communicate with workers.
"""
from __future__ import annotations

import json
import re
from typing import Any

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
ALLOWED_TASK_TYPES = frozenset({"resource_probe", "health_check", "model_evaluation"})
ALLOWED_STATES = frozenset({"queued", "assigned", "running", "succeeded", "failed", "cancelled"})
TRANSITIONS = {
    "queued": frozenset({"assigned", "cancelled"}),
    "assigned": frozenset({"running", "queued", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


def validate_task_request(task_id: str, task_type: str,
                          parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate a bounded JSON task description; never interpret shell/code."""
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("task_id must contain 3-64 safe characters.")
    if task_type not in ALLOWED_TASK_TYPES:
        raise ValueError("task_type is not allowlisted.")
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a JSON object.")
    try:
        encoded = json.dumps(parameters, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("parameters must contain finite JSON values only.") from None
    if len(encoded.encode("utf-8")) > 16_384:
        raise ValueError("task parameters exceed the 16 KiB limit.")
    forbidden = {"command", "shell", "script", "code", "executable", "url"}
    if any(str(key).lower() in forbidden for key in parameters):
        raise ValueError("Executable or externally-directed task fields are forbidden.")
    return {
        "task_id": task_id,
        "task_type": task_type,
        "parameters": parameters,
        "state": "queued",
        "dispatch_enabled": False,
    }


def validate_transition(current_state: str, next_state: str) -> None:
    """Raise unless the requested state transition is explicitly permitted."""
    if current_state not in ALLOWED_STATES or next_state not in ALLOWED_STATES:
        raise ValueError("Unknown task state.")
    if next_state not in TRANSITIONS[current_state]:
        raise ValueError(f"Transition {current_state} -> {next_state} is not allowed.")
