"""Download a large Arabic research corpus into quarantine, never training data.

The OpenITI-derived Hugging Face dataset declares CC0 for its packaging, but
OpenITI's own documentation states that the underlying corpus is CC BY-NC-SA
4.0. This downloader preserves that restriction and does not approve training
or commercial use. It is an acquisition/audit step only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATASETS = {
    "openiti_chunked": {
        "repo_id": "mittagessen/openiti_chunked",
        "revision": "edb9823fb63b544a5cd7889b835a2f85146f031a",
        "estimated_download_bytes": 17_900_426_679,
        "estimated_unpacked_bytes": 38_026_110_415,
        "hub_declared_license": "CC0-1.0 (dataset packaging declaration)",
        "upstream_corpus": "OpenITI release 2023.1.8",
        "upstream_license": "CC BY-NC-SA 4.0 (OpenITI release terms)",
        "training_eligible": False,
        "commercial_use_eligible": False,
        "reason": (
            "The upstream OpenITI release is published under CC BY-NC-SA 4.0. "
            "The Hugging Face CC0 declaration cannot be assumed to relicense "
            "the underlying source texts. Exclude from commercial Jon2 training."
        ),
        "allow_patterns": ["README.md", "data/*.parquet"],
    }
}


def validate_quarantine_destination(destination: Path) -> Path:
    """Reject any path that resolves inside a training-data directory."""
    resolved = destination.expanduser().resolve()
    forbidden_names = {"training_data", "approved_training_data"}
    if any(part.casefold() in forbidden_names for part in resolved.parts):
        raise ValueError(
            "Dataset acquisition must remain quarantined outside every training_data directory."
        )
    if resolved == Path("/") or resolved == Path.home().resolve():
        raise ValueError("Choose a dedicated quarantine folder, not a broad root/home directory.")
    return resolved


def build_manifest(dataset_name: str, destination: Path, snapshot_path: Path) -> dict:
    item = DATASETS[dataset_name]
    files = []
    total_bytes = 0
    for path in sorted(snapshot_path.rglob("*")):
        if path.is_file() and ".cache" not in path.parts:
            size = path.stat().st_size
            total_bytes += size
            files.append({"relative_path": str(path.relative_to(snapshot_path)), "bytes": size})
    return {
        "manifest_version": 1,
        "dataset_key": dataset_name,
        "repo_id": item["repo_id"],
        "revision": item["revision"],
        "destination": str(destination),
        "downloaded_files": files,
        "downloaded_file_count": len(files),
        "downloaded_bytes": total_bytes,
        "estimated_download_bytes": item["estimated_download_bytes"],
        "estimated_unpacked_bytes": item["estimated_unpacked_bytes"],
        "hub_declared_license": item["hub_declared_license"],
        "upstream_corpus": item["upstream_corpus"],
        "upstream_license": item["upstream_license"],
        "training_eligible": False,
        "commercial_use_eligible": False,
        "quarantine_status": "QUARANTINED_NOT_APPROVED",
        "approval_created": False,
        "approval_manifest_modified": False,
        "reason": item["reason"],
        "required_next_step": (
            "Human rights review of the upstream release, source-level rights, "
            "intended use, and commercial restrictions. This download is not "
            "permission to train or deploy."
        ),
    }


def download_dataset(dataset_name: str, destination: Path, confirm_large_download: bool) -> dict:
    if dataset_name not in DATASETS:
        raise ValueError(
            f"Unsupported dataset: {dataset_name}. Only the explicitly quarantined "
            "OpenITI candidate is configured. ArabicText-Large remains blocked "
            "because its upstream source permissions are unresolved."
        )
    if not confirm_large_download:
        raise ValueError(
            "This dataset is about 17.9 GB compressed and 38.0 GB unpacked. "
            "Pass --confirm-large-download only after checking available storage."
        )

    item = DATASETS[dataset_name]
    safe_destination = validate_quarantine_destination(destination)
    safe_destination.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "Missing optional dependency. Install requirements-data.txt first."
        ) from exc

    snapshot_path = Path(snapshot_download(
        repo_id=item["repo_id"],
        repo_type="dataset",
        revision=item["revision"],
        local_dir=str(safe_destination),
        allow_patterns=item["allow_patterns"],
        max_workers=4,
    )).resolve()

    manifest = build_manifest(dataset_name, safe_destination, snapshot_path)
    manifest_path = safe_destination / "acquisition_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": manifest["quarantine_status"],
        "downloaded_file_count": manifest["downloaded_file_count"],
        "downloaded_bytes": manifest["downloaded_bytes"],
        "manifest_path": str(manifest_path),
        "training_eligible": False,
        "commercial_use_eligible": False,
    }, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="openiti_chunked")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--confirm-large-download", action="store_true")
    args = parser.parse_args()
    try:
        download_dataset(
            args.dataset,
            Path(args.destination),
            confirm_large_download=args.confirm_large_download,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
