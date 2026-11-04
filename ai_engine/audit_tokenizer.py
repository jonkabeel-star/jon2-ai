"""Measure how Jon2's byte-level BPE tokenizer represents real corpus text."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tokenizer import ByteBPETokenizer

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def _sample_report(tokenizer: ByteBPETokenizer, label: str, text: str) -> dict:
    encoded = tokenizer.encode(text)
    byte_tokens = sum(token_id < 256 for token_id in encoded)
    merged_tokens = len(encoded) - byte_tokens
    decoded = tokenizer.decode(encoded)
    utf8_bytes = len(text.encode("utf-8"))
    return {
        "label": label,
        "characters": len(text),
        "utf8_bytes": utf8_bytes,
        "tokens": len(encoded),
        "byte_fallback_tokens": byte_tokens,
        "merged_tokens": merged_tokens,
        "byte_fallback_percentage": round(100 * byte_tokens / len(encoded), 4) if encoded else 0.0,
        "utf8_bytes_per_token": round(utf8_bytes / len(encoded), 4) if encoded else 0.0,
        "round_trip_exact": decoded == text,
    }


def analyze_text(text: str, vocab_size: int = 512, min_frequency: int = 2) -> dict:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("Cannot audit an empty corpus.")
    tokenizer = ByteBPETokenizer.train(
        text, vocab_size=vocab_size, min_frequency=min_frequency
    )
    overall = _sample_report(tokenizer, "full_corpus", text)
    samples = [
        _sample_report(tokenizer, "arabic", "اللغة العربية جميلة، وهذا اختبار لفهم النصوص."),
        _sample_report(tokenizer, "english", "Jon2 AI builds tools for language and reasoning."),
        _sample_report(tokenizer, "mixed", "Jon2 AI يفهم العربية والإنجليزية معًا."),
        _sample_report(tokenizer, "emoji_and_symbols", "مرحبًا 🚀 😊 — 123 #AI"),
    ]
    return {
        "report_version": 1,
        "tokenizer": "Jon2 byte-level BPE",
        "configured_vocab_size": vocab_size,
        "actual_vocab_size": tokenizer.vocab_size,
        "merge_count": len(tokenizer.merges),
        "min_pair_frequency": min_frequency,
        "corpus": overall,
        "sample_suites": samples,
        "arabic_character_count": len(ARABIC_RE.findall(text)),
        "latin_character_count": len(LATIN_RE.findall(text)),
        "all_samples_round_trip_exact": all(item["round_trip_exact"] for item in [overall, *samples]),
        "interpretation": (
            "Byte fallback preserves unseen text but a high fallback rate means the tokenizer "
            "has not learned compact merges for that sample. Compression is a tokenizer "
            "efficiency measure, not evidence of language understanding or model quality."
        ),
    }


def analyze_directory(data_dir: Path, vocab_size: int = 1000, min_frequency: int = 2) -> dict:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Training data directory not found: {data_dir}")
    files = sorted(path for path in data_dir.rglob("*.txt") if path.is_file())
    if not files:
        raise ValueError(f"No .txt training files found in {data_dir}")
    texts = [path.read_text(encoding="utf-8") for path in files]
    combined = "\n".join(texts)
    report = analyze_text(combined, vocab_size=vocab_size, min_frequency=min_frequency)
    report["source_files"] = [
        {"file": path.relative_to(data_dir).as_posix(), "characters": len(content)}
        for path, content in zip(files, texts)
    ]
    report["source_file_count"] = len(files)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Jon2 BPE tokenization efficiency.")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--vocab-size", type=int, default=512)
    parser.add_argument("--min-frequency", type=int, default=2)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = analyze_directory(
        Path(args.data), vocab_size=args.vocab_size, min_frequency=args.min_frequency
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
