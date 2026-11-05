"""Heartbeat-only Jon2 Compute worker agent.

This client reports local capacity to an already-enrolled Jon2 worker.
It never enrolls itself, receives jobs, or executes remote code.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

try:
    from .resource_probe import inspect_resources
except ImportError:  # Support execution as: python -m compute.worker_agent
    from compute.resource_probe import inspect_resources


def validate_api_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("JON2_COMPUTE_API_URL must be an absolute HTTPS URL.")
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and parsed.hostname not in local_hosts:
        raise ValueError("Remote worker connections must use HTTPS.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API URL must not contain credentials, query, or fragment.")
    return value


def _clean_entry(value: Any, limit: int = 100) -> str:
    # Registry stores comma-separated entries; remove delimiters/control chars.
    cleaned = "".join(
        char for char in str(value)
        if char != "," and ord(char) >= 32 and ord(char) != 127
    ).strip()
    return cleaned[:limit]


def build_heartbeat_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    accelerators = snapshot.get("accelerators") or []
    types = []
    names = []
    for device in accelerators[:8]:
        device_type = _clean_entry(device.get("type", ""))
        device_name = _clean_entry(device.get("name", ""))
        if device_type:
            types.append(device_type)
        if device_name:
            names.append(device_name)
    total = memory.get("total_bytes")
    if total is None:
        total = 0
    return {
        "cpu_count": max(1, min(int(cpu.get("process_affinity_count") or cpu.get("logical_count") or 1), 4096)),
        "memory_total_bytes": max(0, min(int(total), 2**60)),
        "accelerator_types": types,
        "accelerator_names": names,
    }


def send_heartbeat(api_url: str, node_id: str, token: str,
                   payload: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    base = validate_api_url(api_url)
    if not node_id or len(node_id) > 64 or any(
        not (char.isalnum() or char in "._-") for char in node_id
    ):
        raise ValueError("JON2_WORKER_ID contains unsupported characters.")
    if not token or len(token) < 32:
        raise ValueError("JON2_WORKER_TOKEN is missing or too short.")
    url = f"{base}/api/compute/workers/{quote(node_id, safe='')}/heartbeat"
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Jon2-Compute-Worker/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        # Never include request headers or credentials in raised messages.
        raise RuntimeError(f"Jon2 heartbeat rejected (HTTP {error.code}).") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Jon2 heartbeat connection failed.") from None
    if not isinstance(result, dict) or result.get("accepted") is not True:
        raise RuntimeError("Jon2 server did not accept the heartbeat.")
    return result


def run(interval_seconds: int = 30) -> None:
    api_url = validate_api_url(os.getenv("JON2_COMPUTE_API_URL", ""))
    node_id = os.getenv("JON2_WORKER_ID", "")
    token = os.getenv("JON2_WORKER_TOKEN", "")
    if interval_seconds < 10:
        raise ValueError("Heartbeat interval must be at least 10 seconds.")
    print("Jon2 worker agent started (heartbeat-only; remote job execution is disabled).")
    while True:
        payload = build_heartbeat_payload(inspect_resources())
        send_heartbeat(api_url, node_id, token, payload)
        print("Heartbeat accepted; local capacity reported.")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    try:
        run(int(os.getenv("JON2_HEARTBEAT_INTERVAL_SECONDS", "30")))
    except KeyboardInterrupt:
        print("\nJon2 worker agent stopped.")
        sys.exit(0)
    except (ValueError, RuntimeError) as error:
        print(f"Jon2 worker agent error: {error}", file=sys.stderr)
        sys.exit(1)
