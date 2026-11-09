"""Read-only Jon2 engineering agent: inspect, diagnose, prioritize, and report.

No LLM is bundled or invoked here. The agent does not pretend to understand
semantic failures, generate code, modify files, create branches, or train.
It prepares a grounded engineering plan for the next controlled capability.
"""
from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quality_evaluator import load_jsonl


def inspect_language_engine(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports = sorted({
        node.names[0].name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) and node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    })
    functions = sorted({
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    })
    return {
        "path": str(path),
        "syntax_valid": True,
        "imports": imports,
        "functions": functions,
        "has_model_loader": "load_model" in functions,
        "has_generation_entrypoint": "generate" in functions,
        "has_evaluation_hook": "evaluate" in functions,
    }


def build_engineering_plan(root: Path, cases_path: Path) -> dict[str, Any]:
    engine_path = root / "ai_engine" / "language_engine.py"
    cases = load_jsonl(cases_path)
    audit = inspect_language_engine(engine_path)
    dialects = sorted({str(row.get("dialect", "unlabeled")) for row in cases})
    tasks = []
    if not audit["has_evaluation_hook"]:
        tasks.append({
            "priority": "high",
            "area": "runtime_evaluation",
            "task": "Add a model adapter that runs the real loaded Jon2 model against the reviewed Arabic benchmark and exports answers.",
            "reason": "The current engine has generation but no built-in benchmark evaluation entrypoint.",
            "automation": "requires_model_runtime",
        })
    if "egyptian" in dialects and "msa" in dialects:
        tasks.append({
            "priority": "high",
            "area": "dialect_quality",
            "task": "Run separate Egyptian Arabic and MSA benchmark evaluations, then have a human review weak examples.",
            "reason": "The benchmark includes both dialect labels; source character counts cannot infer dialect competence.",
            "automation": "requires_real_model_outputs_and_human_review",
        })
    tasks.extend([
        {
            "priority": "high",
            "area": "semantic_judge",
            "task": "Add a separately validated semantic/factuality judge and adversarial tests before using scores to accept changes.",
            "reason": "Keyword matching is only a transparent screening signal, not proof of correctness.",
            "automation": "requires_validated_evaluator",
        },
        {
            "priority": "normal",
            "area": "code_generation",
            "task": "Connect a local/open-weight coding model in an isolated runner; let it propose one-file patches on disposable branches.",
            "reason": "No coding-model inference runtime is currently configured in this repository.",
            "automation": "blocked_until_model_runtime_and_sandbox",
        },
        {
            "priority": "normal",
            "area": "training",
            "task": "Keep training disabled until rights-cleared data, measured token sufficiency, GPU capacity, and human evaluation all pass.",
            "reason": "Existing training preflight is a hard safety gate and must not be bypassed.",
            "automation": "blocked_by_existing_preflight",
        },
    ])
    return {
        "schema_version": 1,
        "project": "Jon2 AI",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_engineering_audit",
        "language_engine": audit,
        "benchmark": {
            "case_count": len(cases),
            "dialect_labels": dialects,
            "model_answers_evaluated": False,
            "reason": "No real model output file was supplied; the agent will not fabricate scores.",
        },
        "code_changes_made": False,
        "training_started": False,
        "tasks": tasks,
        "decision": "The engineering loop is not fully autonomous until a real model runtime can propose patches and a validated evaluator can reject regressions.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Jon2 and produce a safe engineering plan.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--cases", default="ai_engine/evaluation_cases.jsonl")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    cases = Path(args.cases)
    cases = cases if cases.is_absolute() else root / cases
    report = build_engineering_plan(root, cases)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
