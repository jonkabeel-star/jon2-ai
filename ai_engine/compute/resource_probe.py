"""Read-only hardware discovery for the Jon2 Compute control plane.

This module reports resources actually visible to the current process. It does
not provision hardware, start remote workers, or claim quota as owned capacity.
"""
from __future__ import annotations

import os
import platform
from typing import Any


def _linux_meminfo() -> dict[str, int] | None:
    try:
        values: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="ascii") as handle:
            for line in handle:
                key, raw = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable"}:
                    values[key] = int(raw.strip().split()[0]) * 1024
        if "MemTotal" in values:
            return {
                "total_bytes": values["MemTotal"],
                "available_bytes": values.get("MemAvailable", 0),
            }
    except (OSError, ValueError):
        return None
    return None


def _cgroup_memory() -> dict[str, int] | None:
    # Prefer the container limit over host RAM so admission is conservative.
    try:
        with open("/sys/fs/cgroup/memory.max", "r", encoding="ascii") as handle:
            raw_limit = handle.read().strip()
        with open("/sys/fs/cgroup/memory.current", "r", encoding="ascii") as handle:
            raw_current = handle.read().strip()
        if raw_limit != "max":
            limit, current = int(raw_limit), int(raw_current)
            if limit > 0:
                return {
                    "total_bytes": limit,
                    "available_bytes": max(0, limit - current),
                }
    except (OSError, ValueError):
        pass
    return None


def _memory() -> dict[str, int | None]:
    # cgroup limits must take precedence over host-level memory figures.
    limited = _cgroup_memory()
    if limited:
        return limited

    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        return {"total_bytes": int(vm.total), "available_bytes": int(vm.available)}
    except Exception:
        pass

    result = _linux_meminfo()
    if result:
        return result
    return {"total_bytes": None, "available_bytes": None}


def _accelerators() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            for index in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(index)
                devices.append({
                    "type": "cuda",
                    "index": index,
                    "name": props.name,
                    "total_memory_bytes": int(props.total_memory),
                    "available_to_process": True,
                })
        mps_available = bool(
            getattr(torch.backends, "mps", None)
            and torch.backends.mps.is_available()
        )
        if mps_available:
            devices.append({
                "type": "mps",
                "index": 0,
                "name": "Apple Metal Performance Shaders",
                "total_memory_bytes": None,
                "available_to_process": True,
            })
    except Exception:
        # Missing or broken optional torch installation is not a service failure.
        pass
    return devices


def inspect_resources() -> dict[str, Any]:
    """Return a conservative snapshot of resources visible to this process."""
    logical = os.cpu_count() or 1
    try:
        affinity = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity = logical
    memory = _memory()
    accelerators = _accelerators()
    return {
        "schema_version": 1,
        "environment": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "cpu": {
            "logical_count": logical,
            "process_affinity_count": max(1, min(logical, affinity)),
        },
        "memory": memory,
        "accelerators": accelerators,
        "capacity_class": (
            "gpu_visible" if any(d["type"] == "cuda" for d in accelerators)
            else "apple_mps_visible" if any(d["type"] == "mps" for d in accelerators)
            else "cpu_only"
        ),
        "provisioning_status": "not_provisioned_by_this_service",
        "notes": [
            "Only resources visible to this process are reported.",
            "This probe does not reserve, rent, or provision compute.",
            "Memory values may be constrained by the container or runtime.",
        ],
    }


def assess_task(min_memory_gib: float = 2.0, require_gpu: bool = False) -> dict[str, Any]:
    """Assess admission only; never launches the requested workload."""
    if min_memory_gib <= 0:
        raise ValueError("min_memory_gib must be greater than zero")
    snapshot = inspect_resources()
    available = snapshot["memory"]["available_bytes"]
    required = int(min_memory_gib * 1024 ** 3)
    gpu_visible = any(
        item["type"] in {"cuda", "mps"} for item in snapshot["accelerators"]
    )
    memory_ok = available is not None and available >= required
    accepted = bool(memory_ok and (gpu_visible or not require_gpu))
    if require_gpu and not gpu_visible:
        reason = "A supported GPU accelerator (CUDA or Apple MPS) is required but none is visible to this process."
    elif available is None:
        reason = "Available memory could not be measured safely."
    elif not memory_ok:
        reason = "Available memory is below the requested minimum."
    else:
        reason = "Resource checks passed; this is admission assessment only."
    return {
        "accepted_for_execution": accepted,
        "execution_started": False,
        "required_memory_bytes": required,
        "available_memory_bytes": available,
        "gpu_required": require_gpu,
        "gpu_visible": gpu_visible,
        "reason": reason,
    }
