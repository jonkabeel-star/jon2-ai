"""Read-only readiness report for a proposed Jon2 training run.

This command validates source approvals, builds the same deterministic corpus
split/tokenizer as the trainer, and reports actual token/parameter counts.
It never creates model weights, changes checkpoints, or starts training.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from corpus_reader import read_corpus
from model_profiles import describe_profile, estimate_parameters
from source_approval import validate_source_approvals
from tokenizer import ByteBPETokenizer
from train_jon2 import split_corpus_blocks


def assess_readiness(
    *,
    corpus_characters: int,
    train_tokens: int,
    validation_tokens: int,
    parameter_count: int,
    tokenizer_vocab: int,
    target_tokenizer_vocab: int,
    context: int,
    minimum_characters: int,
    minimum_tokens_per_parameter: float,
) -> dict:
    """Return explicit blockers without weakening any trainer safeguards."""
    total_tokens = train_tokens + validation_tokens
    ratio = total_tokens / max(1, parameter_count)
    blockers = []
    if corpus_characters < minimum_characters:
        blockers.append("corpus_below_minimum_characters")
    if train_tokens <= context + 1:
        blockers.append("training_partition_too_short_for_context")
    if validation_tokens <= context + 1:
        blockers.append("validation_partition_too_short_for_context")
    if tokenizer_vocab < target_tokenizer_vocab:
        blockers.append("tokenizer_did_not_reach_profile_vocabulary")
    if ratio < minimum_tokens_per_parameter:
        blockers.append("insufficient_tokens_per_parameter")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "corpus_characters": corpus_characters,
        "training_tokens": train_tokens,
        "validation_tokens": validation_tokens,
        "total_tokens": total_tokens,
        "parameter_count_actual": parameter_count,
        "tokenizer_vocab_actual": tokenizer_vocab,
        "tokenizer_vocab_target": target_tokenizer_vocab,
        "tokens_per_parameter": round(ratio, 6),
        "minimum_tokens_per_parameter": minimum_tokens_per_parameter,
        "context": context,
    }


def _language_counts(text: str) -> dict:
    """Report broad script counts only; this is not dialect or quality detection."""
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    digits = len(re.findall(r"[0-9٠-٩]", text))
    return {
        "arabic_script_characters": arabic,
        "latin_characters": latin,
        "digit_characters": digits,
        "other_characters": max(0, len(text) - arabic - latin - digits),
        "dialect_classification": "not_inferred_requires_human_annotation",
    }


def build_report(
    *,
    data_dir: Path,
    approval_manifest: Path,
    profile_name: str,
    include_jsonl: bool = False,
    minimum_characters: int = 100_000,
    minimum_tokens_per_parameter: float = 10.0,
    seed: int = 42,
) -> dict:
    """Run read-only corpus, approval, tokenizer, and architecture preflight."""
    validate_source_approvals(
        data_dir, approval_manifest, include_jsonl=include_jsonl
    )
    corpus = read_corpus(data_dir, include_jsonl=include_jsonl)
    profile = describe_profile(profile_name)
    train_text, validation_text = split_corpus_blocks(corpus, 0.1, seed)
    tokenizer = ByteBPETokenizer.train(
        train_text,
        vocab_size=profile["tokenizer_vocab_size"],
        min_frequency=2,
    )
    train_tokens = len(tokenizer.encode(train_text))
    validation_tokens = len(tokenizer.encode(validation_text))
    actual_parameters = estimate_parameters(
        width=profile["width"],
        layers=profile["layers"],
        context=profile["context"],
        vocab_size=tokenizer.vocab_size,
    )
    readiness = assess_readiness(
        corpus_characters=len(corpus),
        train_tokens=train_tokens,
        validation_tokens=validation_tokens,
        parameter_count=actual_parameters,
        tokenizer_vocab=tokenizer.vocab_size,
        target_tokenizer_vocab=profile["tokenizer_vocab_size"],
        context=profile["context"],
        minimum_characters=minimum_characters,
        minimum_tokens_per_parameter=minimum_tokens_per_parameter,
    )
    return {
        "report_version": 1,
        "mode": "read_only_preflight_no_training",
        "profile": profile_name,
        "estimated_profile_parameters_at_target_vocab": profile["estimated_parameters"],
        "actual_architecture_parameters": actual_parameters,
        "language_script_audit": _language_counts(corpus),
        "readiness": readiness,
        "warnings": [
            "Script counts do not identify MSA versus Egyptian dialect.",
            "Token counts and validation loss do not prove semantic understanding.",
            "A human must review source quality, factuality, privacy, and rights.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Jon2 data and model training readiness check."
    )
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument(
        "--approval-manifest",
        default="ai_engine/training_data/source_approvals.json",
    )
    parser.add_argument("--profile", choices=sorted(
        __import__("model_profiles").PROFILES
    ), default="arabic_30m")
    parser.add_argument("--include-jsonl", action="store_true")
    parser.add_argument("--minimum-characters", type=int, default=100_000)
    parser.add_argument("--minimum-tokens-per-parameter", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if args.minimum_characters < 1 or args.minimum_tokens_per_parameter < 0:
        parser.error("minimum characters must be positive and token ratio non-negative")

    report = build_report(
        data_dir=Path(args.data),
        approval_manifest=Path(args.approval_manifest),
        profile_name=args.profile,
        include_jsonl=args.include_jsonl,
        minimum_characters=args.minimum_characters,
        minimum_tokens_per_parameter=args.minimum_tokens_per_parameter,
        seed=args.seed,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["readiness"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
