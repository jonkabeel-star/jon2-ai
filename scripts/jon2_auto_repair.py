#!/usr/bin/env python3
"""Safe, test-gated maintenance for Jon2 AI.

Only applies whitespace-only changes to tracked-scope Python source. It never
executes commands found in logs, changes model weights, deletes files, or
pushes directly to the default branch. The workflow decides whether a tested
change can be proposed as a pull request.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


CHECKS: tuple[tuple[str, tuple[str, ...], tuple[int, ...]], ...] = (
    ("python_compile", (sys.executable, "-m", "compileall", "-q", "ai_engine", "tests"), (0,)),
    ("root_tests", (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"), (0,)),
    ("engine_tests", (sys.executable, "-m", "unittest", "discover", "-s", "ai_engine", "-p", "test_*.py", "-v"), (0,)),
    ("runtime_tests", (sys.executable, "-m", "unittest", "discover", "-s", "ai_engine/tests", "-t", ".", "-p", "test_*.py", "-v"), (0,)),
    ("training_data_audit", (sys.executable, "ai_engine/audit_data.py"), (0,)),
    ("arabic_coverage_audit", (sys.executable, "ai_engine/audit_language.py", "--data", "ai_engine/training_data"), (0,)),
    ("tokenizer_audit", (sys.executable, "ai_engine/audit_tokenizer.py", "--data", "ai_engine/training_data"), (0,)),
    ("corpus_privacy_audit", (sys.executable, "ai_engine/audit_corpus_quality.py", "--data", "ai_engine/training_data"), (0,)),
    ("dataset_inventory", (sys.executable, "ai_engine/dataset_inventory.py", "--data", "ai_engine/training_data"), (0,)),
    ("training_readiness_preflight", (sys.executable, "ai_engine/preflight_training.py", "--profile", "arabic_30m", "--data", "ai_engine/training_data", "--approval-manifest", "ai_engine/training_data/source_approvals.json", "--output", "auto-repair-output/arabic-30m-preflight.json"), (0, 2)),
)


def normalize_python_whitespace(root: Path) -> list[str]:
    """Remove trailing horizontal whitespace and ensure final LF, preserving CRLF."""
    changed: list[str] = []
    for base in (root / "ai_engine", root / "tests"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                continue
            raw = path.read_bytes()
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            newline = "\r\n" if "\r\n" in source else "\n"
            lines = source.splitlines(keepends=True)
            fixed_lines = []
            for line in lines:
                if line.endswith("\r\n"):
                    fixed_lines.append(line[:-2].rstrip(" \t") + "\r\n")
                elif line.endswith("\n"):
                    fixed_lines.append(line[:-1].rstrip(" \t") + "\n")
                else:
                    fixed_lines.append(line.rstrip(" \t"))
            fixed = "".join(fixed_lines)
            if fixed and not fixed.endswith(("\n", "\r")):
                fixed += newline
            updated = fixed.encode("utf-8")
            if updated != raw:
                path.write_bytes(updated)
                changed.append(path.relative_to(root).as_posix())
    return changed


def run_checks(root: Path) -> list[dict]:
    """Run a fixed allowlist of repository checks; never interpret log text as code."""
    output_dir = root / "auto-repair-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, command, accepted_codes in CHECKS:
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=900,
            )
            result = {
                "name": name,
                "command": list(command),
                "exit_code": completed.returncode,
                "accepted_exit_codes": list(accepted_codes),
                "passed": completed.returncode in accepted_codes,
                "output": completed.stdout[-30000:],
            }
        except subprocess.TimeoutExpired as exc:
            captured = exc.stdout or ""
            if isinstance(captured, bytes):
                captured = captured.decode("utf-8", errors="replace")
            result = {
                "name": name,
                "command": list(command),
                "exit_code": None,
                "accepted_exit_codes": list(accepted_codes),
                "passed": False,
                "output": str(captured)[-30000:] + "\nCHECK TIMED OUT after 900 seconds.",
            }
        results.append(result)
        print(f"[{'PASS' if result['passed'] else 'FAIL'}] {name}", flush=True)
        if not result["passed"]:
            print(result["output"], flush=True)
            break
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path, default=Path("auto-repair-output/report.json"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report_path = (root / args.report).resolve()
    if not (root / "ai_engine").is_dir() or not (root / "tests").is_dir():
        parser.error("--root must point to the Jon2 repository root")

    changed = normalize_python_whitespace(root)
    print(f"Safe whitespace repairs: {len(changed)} file(s)", flush=True)
    for path in changed:
        print(f"  repaired: {path}", flush=True)

    checks = run_checks(root)
    report = {
        "tool": "Jon2 Auto Repair Engine",
        "version": 1,
        "repair_policy": "whitespace_only_python_source",
        "changed_files": changed,
        "checks": checks,
        "all_checks_passed": bool(checks) and all(item["passed"] for item in checks),
        "automatic_code_rewrites": False,
        "model_checkpoint_changes": False,
        "direct_push": False,
        "human_review": "required_before_merge",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Repair report: {report_path.relative_to(root)}", flush=True)
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
