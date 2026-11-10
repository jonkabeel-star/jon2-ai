"""Safe autonomous planning for Jon2 brain development.

This controller audits the existing corpus and training gates, then emits a
prioritized plan. It never downloads sources, edits project files, starts
training, changes checkpoints, or approves a release.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SAFE_AUTONOMOUS_ACTIONS = [
    "inspect repository configuration",
    "validate exact-file source approvals",
    "run read-only corpus and model readiness preflight",
    "write a metadata-only diagnostic report outside the repository",
]
FORBIDDEN_AUTOMATIC_ACTIONS = [
    "download or ingest unreviewed training sources",
    "approve licences or source rights",
    "start model training or fine-tuning",
    "overwrite or delete checkpoints",
    "change application code or deployment settings",
    "approve public chat release",
]


def _recommendations(blockers: list[str], approval_ok: bool) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    if not approval_ok:
        tasks.append({
            "priority": "critical",
            "task": "Complete human rights review and exact-file SHA-256 approval for every intended training source.",
            "reason": "Training remains blocked until the existing source-approval gate passes.",
        })
    if "insufficient_tokens_per_parameter" in blockers:
        tasks.append({
            "priority": "high",
            "task": "Expand the corpus with diverse, rights-cleared Arabic material and rerun the tokenizer-based preflight.",
            "reason": "The measured token supply is below the configured threshold for the selected model profile.",
        })
    if any("dialect" in item for item in blockers):
        tasks.append({
            "priority": "high",
            "task": "Annotate a reviewed evaluation set for Egyptian Arabic, Modern Standard Arabic, and mixed-register input.",
            "reason": "Script-level character counts do not identify dialect or semantic quality.",
        })
    tasks.extend([
        {
            "priority": "high",
            "task": "Run held-out Arabic answer evaluation and human review before accepting any checkpoint.",
            "reason": "Training completion and passing infrastructure tests do not establish useful language quality.",
        },
        {
            "priority": "normal",
            "task": "Keep retrieval knowledge separate from training data and retain source attribution and freshness metadata.",
            "reason": "New facts can be made available through retrieval without silently changing model weights.",
        },
    ])
    return tasks


def _safe_report_destination(destination: Path, repository_root: Path) -> Path:
    candidate = destination.expanduser()
    # Check before resolve(): resolving first erases the fact that the final
    # path component was a symlink and could redirect a report write.
    if candidate.is_symlink():
        raise ValueError("Diagnostic report destination cannot be a symlink.")
    resolved = candidate.resolve()
    root = repository_root.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("Diagnostic reports must be written outside the Git repository.")
    return resolved


def _write_report_atomically(destination: Path, rendered: str) -> None:
    """Write through a unique, exclusively-created temp file in the same directory."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        # fdopen normally owns/closes the descriptor; ignore an already-closed fd.
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def build_autonomous_report(
    repository_root: Path,
    data_dir: Path,
    approval_manifest: Path,
    profile: str = "arabic_30m",
) -> dict[str, Any]:
    """Inspect readiness without making any training or repository changes."""
    root = repository_root.resolve()
    data_path = (root / data_dir).resolve() if not data_dir.is_absolute() else data_dir.resolve()
    manifest_path = (
        (root / approval_manifest).resolve()
        if not approval_manifest.is_absolute()
        else approval_manifest.resolve()
    )
    try:
        data_path.relative_to(root)
        manifest_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Training data and approval manifest must remain inside the repository workspace.") from exc

    approval_ok = False
    approval_error = None
    try:
        from source_approval import validate_source_approvals

        validate_source_approvals(data_path, manifest_path)
        approval_ok = True
    except (OSError, UnicodeError, ValueError, PermissionError) as exc:
        approval_error = str(exc)

    readiness: dict[str, Any] | None = None
    preflight_error = None
    blockers: list[str] = []
    if approval_ok:
        try:
            from preflight_training import build_report

            measured = build_report(
                data_dir=data_path,
                approval_manifest=manifest_path,
                profile_name=profile,
            )
            readiness = measured.get("readiness", {})
            blockers = list(readiness.get("blockers", []))
        except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
            preflight_error = str(exc)
            blockers.append("preflight_execution_error")
    else:
        blockers.append("source_approval_required")

    ready = bool(approval_ok and readiness and readiness.get("ready") is True)
    status = "ready_for_owner_training_approval" if ready else "blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "project": "Jon2 AI",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_autonomous_brain_builder",
        "status": status,
        "profile": profile,
        "training_started": False,
        "model_weights_changed": False,
        "repository_files_changed": False,
        "public_release_approved": False,
        "source_approval": {
            "passed": approval_ok,
            "error": approval_error,
        },
        "preflight": readiness,
        "preflight_error": preflight_error,
        "blockers": blockers,
        "allowed_automatic_actions": SAFE_AUTONOMOUS_ACTIONS,
        "never_automatic_actions": FORBIDDEN_AUTOMATIC_ACTIONS,
        "next_tasks": _recommendations(blockers, approval_ok),
        "decision": (
            "Preflight is ready, but a separate owner-authorized training run and "
            "post-training human evaluation are still required."
            if ready else
            "Do not train. Resolve the listed blockers, then rerun this read-only assessment."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Safely plan Jon2 brain development without training or modifying project files."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument("--approval-manifest", default="ai_engine/training_data/source_approvals.json")
    parser.add_argument("--profile", default="arabic_30m")
    parser.add_argument("--report", default="", help="Optional JSON report path outside the repository.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = build_autonomous_report(
        root,
        Path(args.data),
        Path(args.approval_manifest),
        profile=args.profile,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        destination = _safe_report_destination(Path(args.report), root)
        _write_report_atomically(destination, rendered)
        print(f"Jon2 autonomous report written: {destination}")
    print(rendered, end="")
    return 0 if report["status"] == "ready_for_owner_training_approval" else 2


if __name__ == "__main__":
    raise SystemExit(main())
