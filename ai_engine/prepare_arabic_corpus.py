"""Prepare a quarantined Arabic Wikipedia corpus for Jon2 review.

This downloads text only. It does NOT approve the source, add it to the
training directory, alter checkpoints, or start training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DATASET_ID = "omarkamali/wikipedia-monthly"
DATASET_REVISION_CONFIGS = ("20260301.ar", "20260301.arz")
DATASET_LICENSE = "CC-BY-SA-4.0"
DATASET_URL = "https://huggingface.co/datasets/omarkamali/wikipedia-monthly"
DATASET_ATTRIBUTION = (
    "Wikipedia Monthly, maintained by Omar Kamali and Omneity Labs, "
    "built from Wikimedia dumps; CC-BY-SA-4.0. "
    "Dataset: https://huggingface.co/datasets/omarkamali/wikipedia-monthly"
)
ARABIC_LETTERS = re.compile(r"[\\u0621-\\u064A\\u066E-\\u06D3]")
URL_OR_EMAIL = re.compile(r"(?:https?://|www\\.|[\\w.+-]+@[\\w.-]+)", re.IGNORECASE)


def clean_article(value: object) -> str:
    """Normalize one article without paraphrasing or inventing content."""
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFC", value)
    text = text.replace("\\x00", " ")
    text = re.sub(r"[\\t\\r\\f\\v]+", " ", text)
    text = re.sub(r" *\\n *", "\\n", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\\n{3,}", "\\n\\n", text).strip()
    if len(text) < 200:
        return ""
    letters = ARABIC_LETTERS.findall(text)
    if len(letters) / max(1, len(re.sub(r"\\s", "", text))) < 0.25:
        return ""
    if URL_OR_EMAIL.search(text):
        return ""
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(output_dir: Path, max_characters_per_language: int) -> dict:
    if max_characters_per_language < 200_000:
        raise ValueError("Use at least 200,000 characters per language cap.")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty: {output_dir}. Choose a new folder."
        )

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "Missing optional dependency. Install it with: pip install datasets"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for config in DATASET_REVISION_CONFIGS:
        language = config.rsplit(".", 1)[1]
        output_file = output_dir / f"wikipedia_{language}_quarantine.txt"
        seen = set()
        total_chars = 0
        article_count = 0
        # Streaming avoids downloading the full multi-language archive.
        rows = load_dataset(
            DATASET_ID,
            config,
            split="train",
            streaming=True,
        )
        with output_file.open("w", encoding="utf-8", newline="\\n") as handle:
            for row in rows:
                text = clean_article(row.get("text"))
                if not text:
                    continue
                fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if fingerprint in seen:
                    continue
                if total_chars + len(text) > max_characters_per_language:
                    break
                seen.add(fingerprint)
                handle.write(text + "\\n\\n")
                total_chars += len(text)
                article_count += 1

        files.append({
            "file": output_file.name,
            "language_config": config,
            "article_count": article_count,
            "character_count": total_chars,
            "sha256": sha256_file(output_file),
        })

    manifest = {
        "dataset": DATASET_ID,
        "dataset_url": DATASET_URL,
        "dataset_configs": list(DATASET_REVISION_CONFIGS),
        "dataset_license": DATASET_LICENSE,
        "attribution_required": DATASET_ATTRIBUTION,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "max_characters_per_language": max_characters_per_language,
        "files": files,
        "approval_status": "PENDING_HUMAN_LEGAL_AND_CONTENT_REVIEW",
        "training_allowed": False,
        "notes": [
            "Files are quarantined and are not part of ai_engine/training_data.",
            "CC-BY-SA-4.0 requires attribution and share-alike compliance.",
            "Review article quality, personal data, sensitive content, and license obligations.",
            "Do not add these files to an approved source manifest until a human approves the exact use.",
            "This download does not train or modify any model weights.",
        ],
    }
    manifest_path = output_dir / "source_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a bounded Arabic Wikipedia sample into quarantine only."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ai_engine/training_data_quarantine/wikipedia_monthly_20260301"),
    )
    parser.add_argument(
        "--max-characters-per-language",
        type=int,
        default=10_000_000,
        help="Maximum accepted characters for each pinned language configuration.",
    )
    args = parser.parse_args()
    try:
        manifest = prepare(args.output_dir, args.max_characters_per_language)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("QUARANTINE ONLY: no source approval, training, or checkpoint change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
