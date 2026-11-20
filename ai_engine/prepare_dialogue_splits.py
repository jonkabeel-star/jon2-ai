"""Prepare an approved, leakage-safe three-way JSONL dialogue split."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dialogue_split import prepare_approved_dialogue_splits


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate exact-file source approvals and create train/validation/test "
            "JSONL partitions. This command does not train a model."
        )
    )
    parser.add_argument("--data", type=Path, required=True, help="Training-data directory.")
    parser.add_argument("--approval-manifest", type=Path, required=True, help="Private exact-file approval manifest.")
    parser.add_argument("--output", type=Path, required=True, help="Output directory outside --data.")
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--test-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = prepare_approved_dialogue_splits(
        data_dir=args.data,
        approval_manifest=args.approval_manifest,
        output_dir=args.output,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
