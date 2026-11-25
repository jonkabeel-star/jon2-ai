"""Fail-closed verification of private Jon2 candidate checkpoint manifests.

This verifies files on the private runner after training. It does not upload,
publish, approve, or promote checkpoints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASELINE_SHA256 = "edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2"
MANIFEST_FORMAT = "jon2-private-candidate-manifest-v2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_candidate_manifest(
    manifest_path: str | Path,
    candidates_dir: str | Path,
    *,
    expected_commit: str | None = None,
) -> dict:
    manifest_input = Path(manifest_path)
    candidates_input = Path(candidates_dir)
    if manifest_input.is_symlink():
        raise ValueError("Candidate manifest must not be a symlink.")
    if candidates_input.is_symlink():
        raise ValueError("Candidate checkpoint directory must not be a symlink.")
    manifest_path = manifest_input.resolve(strict=True)
    candidates_dir = candidates_input.resolve(strict=True)
    if not candidates_dir.is_dir():
        raise ValueError("Candidate checkpoint path must be a directory.")
    if manifest_path.parent != candidates_dir.parent:
        raise ValueError("Candidate manifest must sit beside, not inside, candidates/.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid candidate manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != MANIFEST_FORMAT:
        raise ValueError("Unsupported candidate manifest format.")
    if manifest.get("public_release_approved") is not False:
        raise PermissionError("Candidate manifest must explicitly keep public release unapproved.")
    if manifest.get("human_review_required") is not True:
        raise PermissionError("Candidate manifest must require human semantic review.")
    if expected_commit and manifest.get("git_commit") != expected_commit:
        raise PermissionError("Candidate manifest commit does not match this workflow run.")

    files = manifest.get("files")
    if not isinstance(files, dict) or "best" not in files:
        raise ValueError("Candidate manifest must include a best checkpoint.")
    if set(files) - {"best", "resume"}:
        raise ValueError("Candidate manifest contains an unknown checkpoint role.")

    verified = {}
    for role, entry in files.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Malformed {role} checkpoint entry.")
        filename = entry.get("filename")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in {".", ".."}
            or not filename.endswith(".pt")
        ):
            raise ValueError(f"Unsafe {role} checkpoint filename.")
        path = candidates_dir / filename
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"Missing or unsafe {role} checkpoint file.")
        resolved = path.resolve(strict=True)
        if resolved.parent != candidates_dir:
            raise PermissionError(f"{role} checkpoint resolves outside candidates/.")
        actual_size = resolved.stat().st_size
        actual_sha = sha256_file(resolved)
        if actual_size <= 0:
            raise ValueError(f"{role} checkpoint is empty.")
        if entry.get("size_bytes") != actual_size:
            raise PermissionError(f"{role} checkpoint size does not match its manifest.")
        if entry.get("sha256") != actual_sha:
            raise PermissionError(f"{role} checkpoint SHA-256 does not match its manifest.")
        if actual_sha == BASELINE_SHA256:
            raise PermissionError("Candidate checkpoint matches the protected original baseline.")
        verified[role] = {
            "filename": filename,
            "size_bytes": actual_size,
            "sha256": actual_sha,
        }

    return {
        "verified": True,
        "format": MANIFEST_FORMAT,
        "git_commit": manifest.get("git_commit"),
        "profile": manifest.get("profile"),
        "files": verified,
        "public_release_approved": False,
        "human_review_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify private Jon2 candidate checkpoint hashes.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--candidates-dir", required=True, type=Path)
    parser.add_argument("--expected-commit", default=None)
    args = parser.parse_args()
    report = verify_candidate_manifest(
        args.manifest,
        args.candidates_dir,
        expected_commit=args.expected_commit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
