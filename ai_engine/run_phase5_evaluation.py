"""Run the 100-case Phase 5 benchmark against a private original Jon2 checkpoint.

This runner creates a review report only. It never trains, saves, or modifies weights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jon2_core import generate, load_model


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_phase5_prompts(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    rows = []
    seen = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Line {line_number} must be a JSON object.")
        prompt_id, prompt, language = row.get("id"), row.get("prompt"), row.get("language")
        if not isinstance(prompt_id, str) or not prompt_id.strip() or prompt_id in seen:
            raise ValueError(f"Line {line_number} has a missing or duplicate id.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Prompt {prompt_id} is empty.")
        if language not in ("msa", "egyptian"):
            raise ValueError(f"Prompt {prompt_id} has an unsupported language.")
        if row.get("split") != "evaluation_only" or row.get("training_eligible") is not False:
            raise ValueError(f"Prompt {prompt_id} is not explicitly held out.")
        seen.add(prompt_id)
        rows.append({"id": prompt_id, "prompt": prompt.strip(), "language": language})
    counts = {language: sum(row["language"] == language for row in rows) for language in ("msa", "egyptian")}
    if len(rows) != 100 or counts != {"msa": 50, "egyptian": 50}:
        raise ValueError(f"Expected 100 prompts split 50/50 (MSA/Egyptian); found {len(rows)} and {counts}.")
    return rows


def run_evaluation(checkpoint: Path, prompts_path: Path, output: Path, code_commit: str | None = None) -> dict:
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Private Jon2 checkpoint not found: {checkpoint}")
    prompts = load_phase5_prompts(prompts_path)
    checkpoint_hash = sha256_file(checkpoint)
    model, tokenizer, device = load_model(str(checkpoint))
    if hasattr(tokenizer, "to_dict"):
        tokenizer_data = tokenizer.to_dict()
    else:
        tokenizer_data = {"vocabulary": getattr(tokenizer, "vocabulary", None)}
    tokenizer_hash = hashlib.sha256(
        json.dumps(tokenizer_data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    results = []
    for row in prompts:
        prefix = f"المستخدم: {row['prompt']}\nJon2:"
        try:
            generated = generate(
                model, tokenizer, prefix, device,
                max_new_chars=240, temperature=0.8,
                do_sample=False, stop_sequences=["المستخدم:", "\nالمستخدم:"],
            )
            answer = generated[len(prefix):].strip() if generated.startswith(prefix) else generated.strip()
            results.append({
                "id": row["id"], "language": row["language"], "prompt": row["prompt"],
                "status": "generated" if answer else "empty_output",
                "generated_answer": answer,
                "human_review": {"reviewed": False, "scores": None, "notes": ""},
            })
        except Exception as exc:  # preserve a visible failure; never fabricate an answer
            results.append({
                "id": row["id"], "language": row["language"], "prompt": row["prompt"],
                "status": "failed", "generated_answer": None,
                "error": f"{type(exc).__name__}: {exc}",
                "human_review": {"reviewed": False, "scores": None, "notes": ""},
            })

    report = {
        "project": "Jon2 AI",
        "evaluation_type": "phase5_heldout_human_review",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_sha256": checkpoint_hash,
        "tokenizer_sha256": tokenizer_hash,
        "code_commit": code_commit,
        "device": str(device),
        "prompt_count": len(prompts),
        "generated_count": sum(row["status"] == "generated" for row in results),
        "empty_count": sum(row["status"] == "empty_output" for row in results),
        "failed_count": sum(row["status"] == "failed" for row in results),
        "release_approved": False,
        "human_review_required": True,
        "training_eligible": False,
        "results": results,
        "notice": "Diagnostics and generation do not prove semantic quality. Human review is mandatory. This report does not approve release.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 5 against the private original Jon2 checkpoint.")
    parser.add_argument("--checkpoint", required=True, help="Path to the owner's private original checkpoint.")
    parser.add_argument("--prompts", default="ai_engine/evaluation/phase5_prompts_100.jsonl")
    parser.add_argument("--output", default="phase5-review-report.json")
    parser.add_argument("--code-commit", default=None)
    args = parser.parse_args()
    report = run_evaluation(Path(args.checkpoint), Path(args.prompts), Path(args.output), args.code_commit)
    print(json.dumps({key: report[key] for key in (
        "checkpoint_sha256", "tokenizer_sha256", "device", "prompt_count",
        "generated_count", "empty_count", "failed_count", "release_approved"
    )}, ensure_ascii=False, indent=2))
    print(f"Review report: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
