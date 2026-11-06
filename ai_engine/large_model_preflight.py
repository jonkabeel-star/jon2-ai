"""Capacity estimates for large Jon2 experiments; never allocates model weights."""
from __future__ import annotations

import argparse
import json

TARGET_PARAMETERS = 20_000_000_000
BYTES_PER_GIB = 1024 ** 3


def estimate_storage_gib(parameters: int, bytes_per_parameter: float) -> float:
    if type(parameters) is not int or parameters <= 0:
        raise ValueError("parameters must be a positive integer")
    if not isinstance(bytes_per_parameter, (int, float)) or bytes_per_parameter <= 0:
        raise ValueError("bytes_per_parameter must be positive")
    return parameters * bytes_per_parameter / BYTES_PER_GIB


def estimate_adam_training_gib(parameters: int) -> float:
    """Approximate aggregate state only: 16 bytes/parameter, excluding activations."""
    return estimate_storage_gib(parameters, 16)


def build_report(parameters: int = TARGET_PARAMETERS) -> dict:
    return {
        "target_parameters": parameters,
        "weights_only_gib": {
            "fp32": round(estimate_storage_gib(parameters, 4), 2),
            "bf16_fp16": round(estimate_storage_gib(parameters, 2), 2),
            "int8_raw_lower_bound": round(estimate_storage_gib(parameters, 1), 2),
            "int4_raw_lower_bound": round(estimate_storage_gib(parameters, 0.5), 2),
        },
        "full_parameter_adam_state_gib_excluding_activations": round(
            estimate_adam_training_gib(parameters), 2
        ),
        "status": "estimate_only_no_weights_or_training_created",
        "warning": (
            "Real training also needs activations, communication buffers, "
            "temporary tensors, checkpoint staging, and distributed overhead."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate Jon2 large-model memory needs.")
    parser.add_argument("--parameters", type=int, default=TARGET_PARAMETERS)
    args = parser.parse_args()
    print(json.dumps(build_report(args.parameters), indent=2))


if __name__ == "__main__":
    main()
