#!/usr/bin/env python3
"""Analyze trusted CI failures and apply only exact, test-gated safe repairs.

The engine never executes commands from logs, never edits outside ai_engine/
for code repairs, and never changes model weights, training data, secrets, or
deployment workflows. Only verified allowlisted source repairs may be proposed in a review-only pull request.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PROTECTED_PATH_PARTS = {"training_data", "checkpoints", "evaluation", "models", "secrets", "weights"}

CHECKS: tuple[tuple[str, tuple[str, ...], tuple[int, ...]], ...] = (
    ("python_compile", (sys.executable, "-m", "compileall", "-q", "ai_engine", "tests"), (0,)),
    ("frontend_js_syntax", (sys.executable, "tests/check_frontend_js.py", "index.html"), (0,)),
    ("node_server_checks", ("npm", "run", "check", "--prefix", "server"), (0,)),
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
            if any(part in {".git", "__pycache__", ".venv", "venv"} | PROTECTED_PATH_PARTS for part in path.parts):
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


def snapshot_repair_scope(root: Path) -> dict[Path, bytes]:
    """Capture original bytes for every eligible Python source before mutation."""
    snapshot: dict[Path, bytes] = {}
    for base in (root / "ai_engine", root / "tests"):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                resolved = path.resolve()
                relative = resolved.relative_to(root.resolve())
            except (OSError, ValueError):
                continue
            if (
                relative.parts
                and relative.parts[0] in {"ai_engine", "tests"}
                and not any(part in PROTECTED_PATH_PARTS for part in relative.parts)
                and resolved.is_file()
            ):
                snapshot[resolved] = resolved.read_bytes()
    return snapshot


def restore_snapshot(snapshot: dict[Path, bytes]) -> list[str]:
    """Restore original source bytes after any failed validation check."""
    restored: list[str] = []
    for path, original in snapshot.items():
        try:
            if path.is_file() and path.read_bytes() != original:
                path.write_bytes(original)
                restored.append(str(path))
        except OSError:
            # A failed restore is surfaced in the report rather than hidden.
            restored.append(f"RESTORE_FAILED:{path}")
    return sorted(restored)



# Exact, reviewable repairs for a small allowlist of missing standard-library imports.
# This is deliberately not an unrestricted code generator.
SAFE_IMPORTS: dict[str, str] = {
    "json": "import json",
    "re": "import re",
    "math": "import math",
    "os": "import os",
    "sys": "import sys",
    "Path": "from pathlib import Path",
    "Counter": "from collections import Counter",
    "defaultdict": "from collections import defaultdict",
    "timezone": "from datetime import timezone",
}
NAME_ERROR = re.compile(r"NameError:\s*name ['\"]([A-Za-z_][A-Za-z0-9_]*)['\"] is not defined")
TRACEBACK_FILE = re.compile(r'File ["\']([^"\']+\.py)["\']')


def _repo_python_file(root: Path, raw_path: str) -> Path | None:
    """Resolve only existing Python files beneath ai_engine/."""
    candidate = Path(raw_path)
    options = [candidate] if candidate.is_absolute() else [root / candidate]
    if candidate.is_absolute():
        parts = candidate.parts
        for index, part in enumerate(parts):
            if part == "ai_engine":
                options.append(root.joinpath(*parts[index:]))
    for option in options:
        try:
            resolved = option.resolve()
            relative = resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if (relative.parts and relative.parts[0] == "ai_engine"
            and not any(part in PROTECTED_PATH_PARTS for part in relative.parts)
            and resolved.is_file() and resolved.suffix == ".py"):
            return resolved
    return None


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def _import_insertion_line(tree: ast.Module, lines: list[str]) -> int:
    """Return a zero-based insertion point after module docstring/future imports."""
    line = 0
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Str, ast.Constant)):
        if isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            line = body[0].end_lineno or body[0].lineno
        elif isinstance(body[0].value, ast.Str):
            line = body[0].end_lineno or body[0].lineno
    for node in body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            line = max(line, node.end_lineno or node.lineno)
    # Preserve shebang and encoding declarations when no module docstring exists.
    while line < min(2, len(lines)) and (
        lines[line].startswith("#!") or "coding" in lines[line]
    ):
        line += 1
    return line


def generate_safe_repairs(root: Path, log_text: str) -> list[dict]:
    """Turn a recognized NameError into a minimal import-only patch."""
    match = NAME_ERROR.search(log_text)
    if not match:
        return [{"status": "no_safe_rule", "reason": "No allowlisted NameError signature found."}]
    missing_name = match.group(1)
    import_line = SAFE_IMPORTS.get(missing_name)
    if not import_line:
        return [{
            "status": "unsupported",
            "reason": "The missing symbol is not in the standard-library import allowlist.",
            "symbol": missing_name,
        }]

    # Use the traceback immediately preceding this NameError. CI logs may contain multiple failures.
    preceding_log = log_text[:match.start()]
    trace_files = TRACEBACK_FILE.findall(preceding_log)
    target = next(
        (resolved for raw in reversed(trace_files) if (resolved := _repo_python_file(root, raw)) is not None),
        None,
    )
    if target is None:
        return [{
            "status": "unsupported",
            "reason": "No traceback file under ai_engine/ could be resolved.",
            "symbol": missing_name,
        }]

    source = target.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(target))
    except SyntaxError as exc:
        return [{
            "status": "blocked",
            "reason": "The target file has a syntax error; import insertion is not safe.",
            "file": target.relative_to(root).as_posix(),
            "line": exc.lineno,
        }]
    if missing_name in _imported_names(tree):
        return [{
            "status": "already_imported",
            "reason": "The missing symbol is already imported; no patch was applied.",
            "file": target.relative_to(root).as_posix(),
            "symbol": missing_name,
        }]

    lines = source.splitlines(keepends=True)
    insertion = _import_insertion_line(tree, lines)
    newline = "\r\n" if "\r\n" in source else "\n"
    lines.insert(insertion, import_line + newline)
    target.write_text("".join(lines), encoding="utf-8", newline="")
    return [{
        "status": "patched",
        "rule": "missing_standard_library_import",
        "file": target.relative_to(root).as_posix(),
        "symbol": missing_name,
        "patch": import_line,
        "line": insertion + 1,
    }]


def diagnose_failure(log_text: str) -> list[dict]:
    """Classify common failures without attempting uncertain fixes."""
    rules = (
        ("missing_dependency", r"ModuleNotFoundError: No module named .+",
         "Check the approved dependency manifest and the runtime environment."),
        ("import_symbol_mismatch", r"ImportError: cannot import name .+",
         "Compare the imported symbol with the installed package API."),
        ("missing_path", r"FileNotFoundError: .+",
         "Verify the path, working directory, and whether the file should exist."),
        ("function_signature_mismatch", r"TypeError: .*(unexpected keyword argument|positional argument|keyword-only argument).*",
         "Compare the function definition with every call site."),
        ("missing_attribute", r"AttributeError: .+",
         "Verify the object type and the supported module or class API."),
        ("undefined_symbol", r"NameError: name .+ is not defined",
         "Check spelling, scope, and whether an import is missing."),
    )
    findings = []
    for category, pattern, guidance in rules:
        for match in re.finditer(pattern, log_text):
            findings.append({
                "category": category,
                "evidence": match.group(0)[:500],
                "action": "diagnostic_only",
                "guidance": guidance,
            })
    return findings


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
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path, default=Path("auto-repair-output/report.json"))
    parser.add_argument("--logs", type=Path, help="Path to a failed GitHub Actions log; logs are parsed as data only.")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report_path = (root / args.report).resolve()
    if not (root / "ai_engine").is_dir() or not (root / "tests").is_dir():
        parser.error("--root must point to the Jon2 repository root")

    # Keep a byte-for-byte recovery point before either whitespace cleanup or code repair.
    original_snapshot = snapshot_repair_scope(root)
    repair_proposals: list[dict] = []
    diagnostics: list[dict] = []
    if args.logs:
        log_path = args.logs if args.logs.is_absolute() else root / args.logs
        if log_path.is_file():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            diagnostics = diagnose_failure(log_text)
            repair_proposals = generate_safe_repairs(root, log_text)
        else:
            repair_proposals = [{"status": "no_log", "reason": "The supplied log file was not found."}]

    changed = normalize_python_whitespace(root)
    for proposal in repair_proposals:
        if proposal.get("status") == "patched":
            target = proposal.get("file")
            if isinstance(target, str) and target not in changed:
                changed.append(target)
    changed.sort()
    print(f"Safe allowlisted repairs: {len(changed)} file(s)", flush=True)
    for path in changed:
        print(f"  repaired: {path}", flush=True)

    checks = run_checks(root)
    all_checks_passed = bool(checks) and all(item["passed"] for item in checks)
    rolled_back_files: list[str] = []
    if not all_checks_passed:
        rolled_back_files = restore_snapshot(original_snapshot)
        print(f"Validation failed; rolled back {len(rolled_back_files)} source file(s).", flush=True)

    report = {
        "tool": "Jon2 Auto Repair Engine",
        "version": 1,
        "repair_policy": "allowlisted_standard_library_imports_and_python_whitespace_only",
        "coverage": ["python", "function_signature_diagnostics", "path_failure_diagnostics", "dependency_diagnostics", "frontend_inline_javascript", "node_server_syntax_and_release_gate_tests"],
        "unsupported_failures_are_diagnostic_only": True,
        "repair_proposals": repair_proposals,
        "diagnostics": diagnostics,
        "changed_files": changed,
        "rolled_back_files": rolled_back_files,
        "changes_retained": all_checks_passed and bool(changed),
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "automatic_code_rewrites": any(item.get("status") == "patched" for item in repair_proposals),
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
