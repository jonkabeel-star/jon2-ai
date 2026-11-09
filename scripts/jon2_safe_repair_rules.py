"""Conservative, evidence-based repair suggestions for paths, symbols and dependencies.

This module never edits source, installs packages, or executes log content.
All suggestions are bounded to repository source roots and require human review.
"""
from __future__ import annotations

import ast
import difflib
import re
import sys
from pathlib import Path, PurePosixPath

SOURCE_ROOTS = ("ai_engine", "scripts", "tests")
MISSING_PATH = re.compile(r"(?:FileNotFoundError|No such file or directory)[: ]+['\"]?([^'\"\n]+)")
MISSING_MODULE = re.compile(r"No module named ['\"]([^'\"]+)['\"]")
MISSING_ATTRIBUTE = re.compile(r"(?:has no attribute|attribute) ['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")


def _source_files(root: Path):
    for folder in SOURCE_ROOTS:
        base = root / folder
        if base.is_dir():
            yield from (p for p in base.rglob("*.py") if p.is_file())


def suggest_path_repair(root: Path, log_text: str) -> dict:
    """Suggest a unique same-basename path only; never create or rewrite files."""
    match = MISSING_PATH.search(log_text)
    if not match:
        return {"status": "no_match"}
    raw = match.group(1).strip()
    name = PurePosixPath(raw.replace("\\", "/")).name
    if not name or name in {".", ".."}:
        return {"status": "blocked", "reason": "Invalid or empty path"}
    candidates = sorted(
        p.relative_to(root).as_posix()
        for p in _source_files(root)
        if p.name == name
    )
    if len(candidates) == 1:
        return {"status": "suggestion", "missing_path": raw[:300],
                "candidate": candidates[0], "evidence": "unique exact filename under an approved source root",
                "source_changed": False}
    return {"status": "ambiguous" if candidates else "no_candidate",
            "missing_path": raw[:300], "candidates": candidates[:10],
            "source_changed": False}


def _symbol_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def suggest_symbol_repair(root: Path, log_text: str) -> dict:
    """Suggest a close, unique existing symbol; never rewrite a call or attribute."""
    match = MISSING_ATTRIBUTE.search(log_text)
    if not match:
        return {"status": "no_match"}
    missing = match.group(1)
    names = set()
    evidence_files = []
    for path in _source_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        local = _symbol_names(tree)
        if local:
            names.update(local)
    ranked = difflib.get_close_matches(missing, sorted(names), n=2, cutoff=0.82)
    if len(ranked) == 1:
        candidate = ranked[0]
        for path in _source_files(root):
            try:
                if candidate in _symbol_names(ast.parse(path.read_text(encoding="utf-8"))):
                    evidence_files.append(path.relative_to(root).as_posix())
            except (OSError, UnicodeError, SyntaxError):
                pass
        return {"status": "suggestion", "missing_symbol": missing,
                "candidate": candidate, "evidence_files": sorted(set(evidence_files))[:5],
                "requires_behavioral_test": True, "source_changed": False}
    return {"status": "ambiguous" if ranked else "no_candidate",
            "missing_symbol": missing, "candidates": ranked,
            "source_changed": False}


def diagnose_dependency(root: Path, log_text: str) -> dict:
    """Classify a missing import against stdlib and declared requirements; install nothing."""
    match = MISSING_MODULE.search(log_text)
    if not match:
        return {"status": "no_match", "installed_anything": False}
    module = match.group(1).split(".", 1)[0]
    if module in getattr(sys, "stdlib_module_names", set()):
        return {"status": "python_standard_library", "module": module,
                "action": "check_python_version_or_import_name", "installed_anything": False}
    requirements = root / "requirements.txt"
    declared = set()
    if requirements.is_file():
        for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines():
            item = line.strip()
            if item and not item.startswith(("#", "-")):
                declared.add(re.split(r"[<=>~!;\[]", item, 1)[0].strip().lower().replace("_", "-"))
    normalized = module.lower().replace("_", "-")
    if normalized in declared:
        status, action = "declared_dependency_missing_at_runtime", "install_from_locked_project_requirements_in_the_deployment_environment"
    else:
        status, action = "undeclared_or_unmapped_dependency", "human_review_required_check_import_to_distribution_mapping_before_editing_requirements"
    return {"status": status, "module": module, "declared_requirements": sorted(declared),
            "action": action, "automatic_install": False, "installed_anything": False}


def analyze_safe_repair_options(root: Path, log_text: str) -> dict:
    return {
        "path": suggest_path_repair(root, log_text),
        "symbol": suggest_symbol_repair(root, log_text),
        "dependency": diagnose_dependency(root, log_text),
        "automatic_source_rewrite": False,
        "automatic_package_install": False,
    }
