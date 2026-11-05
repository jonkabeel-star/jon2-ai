"""Safely download an owner-approved Jon2 Arabic checkpoint.

This script is deliberately fail-closed. It does not download anything unless:
- the owner has reviewed and approved source-level data rights;
- the owner has accepted the model host's access terms;
- an immutable 40-character model revision is supplied.

Weights and credentials are kept outside the public Git repository.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "inception42/Jais-2-8B-Chat"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def require_yes(name: str) -> None:
    if os.getenv(name, "").strip() != "YES":
        raise SystemExit(
            f"STOP: set {name}=YES only after you personally complete that approval."
        )


def main() -> None:
    require_yes("JON2_MODEL_RIGHTS_APPROVED")
    require_yes("JON2_HF_ACCESS_ACCEPTED")

    revision = os.getenv("JON2_MODEL_REVISION", "").strip().lower()
    if not SHA_RE.fullmatch(revision):
        raise SystemExit(
            "STOP: JON2_MODEL_REVISION must be the reviewed immutable 40-character "
            "commit SHA from the official model repository; 'main' is not accepted."
        )

    target_raw = os.getenv("JON2_MODEL_TARGET", "").strip()
    if not target_raw:
        raise SystemExit("STOP: set JON2_MODEL_TARGET to private storage outside this repo.")
    target = Path(target_raw).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[3]
    if target == repo_root or repo_root in target.parents:
        raise SystemExit("STOP: model weights must not be stored inside the Git repository.")
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"STOP: target directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit(
            "Install huggingface_hub in the private runtime environment first."
        ) from exc

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    print(f"Downloading approved checkpoint {MODEL_ID} at immutable revision {revision}")
    snapshot_download(
        repo_id=MODEL_ID,
        revision=revision,
        local_dir=str(target),
        token=token,
        local_files_only=False,
    )

    files = []
    for path in sorted(p for p in target.rglob("*") if p.is_file()):
        if ".cache" in path.parts:
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        files.append({
            "path": str(path.relative_to(target)),
            "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
        })

    manifest = {
        "model_id": MODEL_ID,
        "revision": revision,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rights_approval": "owner_asserted_yes",
        "hub_access_terms_acceptance": "owner_asserted_yes",
        "files": files,
        "warning": (
            "This manifest records downloaded file hashes; it is not legal advice "
            "or proof that upstream training-data rights are cleared."
        ),
    }
    manifest_path = target / "jon2_checkpoint_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"SUCCESS: downloaded {len(files)} files to private storage: {target}")
    print(f"SHA-256 manifest: {manifest_path}")


if __name__ == "__main__":
    main()
