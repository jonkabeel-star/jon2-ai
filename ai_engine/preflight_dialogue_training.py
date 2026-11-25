"""Read-only capacity preflight for the approved three-way dialogue pipeline.

Loads only train/validation partitions. The held-out test partition is hash-checked
by dialogue_training but is never decoded, tokenized, or used for readiness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dialogue_training import load_dialogue_training_partitions
from model_profiles import describe_profile, estimate_parameters
from preflight_training import assess_readiness, should_skip_exact_tokenizer
from tokenizer import ByteBPETokenizer


def build_report(*, data_dir: Path, approval_manifest: Path,
                 dialogue_splits_dir: Path, profile_name: str,
                 minimum_characters: int = 1_000_000,
                 minimum_tokens_per_parameter: float = 20.0,
                 seed: int = 42) -> dict:
    train_text, validation_text, metadata = load_dialogue_training_partitions(
        dialogue_splits_dir, data_dir, approval_manifest
    )
    profile = describe_profile(profile_name)
    target_parameters = profile["estimated_parameters"]
    probe_vocab = min(profile["tokenizer_vocab_size"], 512)
    probe = ByteBPETokenizer.train(train_text, vocab_size=probe_vocab, min_frequency=2)
    probe_train_tokens = len(probe.encode(train_text))
    probe_validation_tokens = len(probe.encode(validation_text))
    probe_total = probe_train_tokens + probe_validation_tokens
    skipped = should_skip_exact_tokenizer(
        probe_tokens=probe_total,
        target_parameters=target_parameters,
        minimum_tokens_per_parameter=minimum_tokens_per_parameter,
    )

    if skipped:
        train_tokens = probe_train_tokens
        validation_tokens = probe_validation_tokens
        parameter_count = target_parameters
        actual_vocab = None
        mode = "dialogue_probe_upper_bound_no_training"
    else:
        tokenizer = ByteBPETokenizer.train(
            train_text,
            vocab_size=profile["tokenizer_vocab_size"],
            min_frequency=2,
        )
        train_tokens = len(tokenizer.encode(train_text))
        validation_tokens = len(tokenizer.encode(validation_text))
        parameter_count = estimate_parameters(
            width=profile["width"],
            layers=profile["layers"],
            context=profile["context"],
            vocab_size=tokenizer.vocab_size,
        )
        actual_vocab = tokenizer.vocab_size
        mode = "dialogue_exact_tokenizer_preflight_no_training"

    readiness = assess_readiness(
        corpus_characters=len(train_text),
        train_tokens=train_tokens,
        validation_tokens=validation_tokens,
        estimated_parameter_count=parameter_count,
        tokenizer_vocab=actual_vocab,
        target_tokenizer_vocab=profile["tokenizer_vocab_size"],
        context=profile["context"],
        minimum_characters=minimum_characters,
        minimum_tokens_per_parameter=minimum_tokens_per_parameter,
    )
    return {
        "report_version": 1,
        "mode": mode,
        "profile": profile_name,
        "profile_parameter_estimate_at_target_vocab": target_parameters,
        "measured_parameter_estimate": parameter_count,
        "tokenizer_vocab_actual": actual_vocab,
        "tokenizer_probe": {
            "vocab_size": probe.vocab_size,
            "target_vocab_size": profile["tokenizer_vocab_size"],
            "exact_target_tokenizer_skipped": skipped,
            "probe_total_tokens": probe_total,
            "probe_tokens_per_estimated_parameter": round(
                probe_total / max(1, target_parameters), 8
            ),
            "interpretation": (
                "Optimistic upper bound: the target tokenizer can only preserve "
                "or reduce token count relative to this deterministic probe."
            ),
        },
        "partition_characters": {
            "train": len(train_text),
            "validation": len(validation_text),
        },
        "readiness": readiness,
        "split_provenance": metadata,
        "warnings": [
            "This is a read-only preflight; it creates no model weights.",
            "The held-out test partition is hash-checked but never decoded or tokenized.",
            "Parameter counts are architecture estimates, not measured trained weights.",
            "Passing capacity checks does not establish semantic understanding.",
            "Human rights, privacy, quality, and semantic review remain mandatory.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for approved three-way Jon2 dialogue training."
    )
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--approval-manifest", required=True, type=Path)
    parser.add_argument("--dialogue-splits-dir", required=True, type=Path)
    parser.add_argument("--profile", choices=("cpu_small", "balanced", "advanced", "arabic_30m", "large_research"), default="arabic_30m")
    parser.add_argument("--minimum-characters", type=int, default=1_000_000)
    parser.add_argument("--minimum-tokens-per-parameter", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.minimum_characters < 1_000_000:
        parser.error("minimum-characters cannot be lower than 1,000,000")
    if args.minimum_tokens_per_parameter < 20.0:
        parser.error("minimum-tokens-per-parameter cannot be lower than 20")
    report = build_report(
        data_dir=args.data,
        approval_manifest=args.approval_manifest,
        dialogue_splits_dir=args.dialogue_splits_dir,
        profile_name=args.profile,
        minimum_characters=args.minimum_characters,
        minimum_tokens_per_parameter=args.minimum_tokens_per_parameter,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["readiness"]["ready"]:
        print("PREFLIGHT BLOCKED: no training was started.")
        return 2
    print("PREFLIGHT PASS: capacity checks only; semantic approval is still pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
