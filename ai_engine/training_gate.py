"""Training is dry-run by default; explicit execute requires every verified gate."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from preflight_training import build_report
from model_profiles import describe_profile


def prepare(data, approvals, profile, checkpoint, minimum_chars=100000, minimum_ratio=10.0):
    report = build_report(
        data_dir=data,
        approval_manifest=approvals,
        profile_name=profile,
        minimum_characters=minimum_chars,
        minimum_tokens_per_parameter=minimum_ratio,
    )
    approval = report.get("source_approval_validation", {})
    approval_passed = (
        approval.get("passed") is True
        and approval.get("approved_file_count", 0) > 0
    )
    try:
        import torch

        cuda = torch.cuda.is_available()
        gpu = torch.cuda.get_device_name(0) if cuda else None
    except Exception:
        cuda, gpu = False, None

    target = checkpoint.resolve()
    ready = bool(
        approval_passed
        and report["readiness"]["ready"]
        and cuda
        and not target.exists()
    )
    blockers = []
    if not approval_passed:
        blockers.append("source_approval_not_verified")
    if not report["readiness"]["ready"]:
        blockers.extend(report["readiness"].get("blockers", []))
    if not cuda:
        blockers.append("cuda_unavailable")
    if target.exists():
        blockers.append("checkpoint_already_exists")

    return {
        "profile": profile,
        "readiness": report["readiness"],
        "source_approval_validation": approval,
        "source_approval_passed": approval_passed,
        "cuda_available": cuda,
        "gpu_name": gpu,
        "checkpoint_path": str(target),
        "checkpoint_path_is_new": not target.exists(),
        "authorized_to_train": ready,
        "training_started": False,
        "training_completed": False,
        "trainer_invoked": False,
        "blockers": blockers,
        "reason": (
            "All gates passed; explicit --execute required."
            if ready
            else "Blocked by verified rights, data/token sufficiency, GPU, or checkpoint checks."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="ai_engine/training_data")
    parser.add_argument(
        "--approvals", default="ai_engine/training_data/source_approvals.json"
    )
    parser.add_argument("--profile", default="arabic_30m")
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--minimum-characters", type=int, default=100000)
    parser.add_argument("--minimum-tokens-per-parameter", type=float, default=10.0)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report", default="artifacts/jon2-training-gate.json")
    args = parser.parse_args()

    if args.minimum_tokens_per_parameter < 10:
        parser.error("Token/parameter guard cannot be lowered below 10.")
    if args.steps < 1:
        parser.error("steps must be positive")
    describe_profile(args.profile)

    checkpoint = Path(args.checkpoint) if args.checkpoint else Path(
        "ai_engine/checkpoints/gated-"
        + args.profile
        + "-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + ".pt"
    )
    result = prepare(
        Path(args.data),
        Path(args.approvals),
        args.profile,
        checkpoint,
        args.minimum_characters,
        args.minimum_tokens_per_parameter,
    )

    if args.execute and result["authorized_to_train"]:
        last = checkpoint.with_name(checkpoint.stem + "-last.pt")
        command = [
            sys.executable,
            "ai_engine/train_jon2.py",
            "--data",
            args.data,
            "--approval-manifest",
            args.approvals,
            "--profile",
            args.profile,
            "--steps",
            str(args.steps),
            "--minimum-tokens-per-parameter",
            str(args.minimum_tokens_per_parameter),
            "--minimum-chars",
            str(args.minimum_characters),
            "--output",
            str(checkpoint),
            "--last-checkpoint",
            str(last),
            "--keep-last",
        ]
        result["trainer_invoked"] = True
        try:
            completed = subprocess.run(command, check=False)
            result["trainer_exit_code"] = completed.returncode
            result["training_started"] = completed.returncode == 0
            result["training_completed"] = completed.returncode == 0
            if completed.returncode != 0:
                result["reason"] = (
                    "All gates passed, but the trainer process failed; inspect "
                    "trainer_exit_code and runtime logs."
                )
        except OSError as exc:
            result["trainer_exit_code"] = 127
            result["trainer_error"] = str(exc)
            result["training_started"] = False
            result["training_completed"] = False
            result["reason"] = "The trainer process could not be launched."
    elif args.execute:
        result["training_blocked"] = True

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["authorized_to_train"]:
        return 2
    if args.execute and not result.get("training_completed", False):
        return result.get("trainer_exit_code", 1) or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
