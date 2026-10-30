"""Download a bounded Arabic training sample for Jon2 AI.

This script downloads data to the local runtime only; it never commits data to GitHub.
Review dataset and underlying source rights before enabling the explicit confirmation flag.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from datasets import load_dataset


DATASET_ID = "Jr23xd23/ArabicText-Large"


def arabic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    arabic = sum("\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f" for c in letters)
    return arabic / len(letters)


def clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="training_data/raw/arabictext_large_sample.txt")
    parser.add_argument("--max-articles", type=int, default=5000)
    parser.add_argument("--max-chars", type=int, default=2_000_000)
    parser.add_argument("--min-article-chars", type=int, default=180)
    parser.add_argument(
        "--confirm-rights-reviewed",
        action="store_true",
        help="Required only after you personally reviewed the dataset and underlying source rights for your intended use.",
    )
    args = parser.parse_args()

    if not args.confirm_rights_reviewed:
        raise SystemExit(
            "STOP: review the dataset card and underlying source rights first. "
            "If approved for your intended training/commercial use, rerun with "
            "--confirm-rights-reviewed."
        )
    if args.max_articles < 1 or args.max_chars < 1000:
        parser.error("max-articles must be positive and max-chars must be at least 1000")

    print(f"Streaming {DATASET_ID}; this is a bounded sample, not the full corpus.")
    dataset = load_dataset(DATASET_ID, split="train", streaming=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    written = 0
    total_chars = 0
    with output.open("w", encoding="utf-8") as handle:
        for row in dataset:
            title = clean_text(str(row.get("title", "")))
            body = clean_text(str(row.get("text", "")))
            article = "\n".join(part for part in (title, body) if part)
            if len(article) < args.min_article_chars or arabic_ratio(article) < 0.60:
                continue
            digest = hashlib.sha256(article.encode("utf-8")).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)

            remaining = args.max_chars - total_chars
            if remaining <= 0:
                break
            article = article[:remaining]
            handle.write(article + "\n\n")
            written += 1
            total_chars += len(article)
            if written % 250 == 0:
                print(f"kept={written} chars={total_chars:,}")
            if written >= args.max_articles or total_chars >= args.max_chars:
                break

    if total_chars < 1000:
        output.unlink(missing_ok=True)
        raise SystemExit("No usable corpus was produced. Check access and dataset format.")

    print("Dataset sample prepared.")
    print(f"Articles kept: {written:,}")
    print(f"Characters written: {total_chars:,}")
    print(f"Output: {output.resolve()}")
    print("Keep the source attribution and license record with this dataset.")


if __name__ == "__main__":
    main()
