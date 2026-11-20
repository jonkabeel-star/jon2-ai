#!/usr/bin/env python3
"""Run held-out Arabic prompts and write a report for mandatory human review.

This script never changes model weights and never grants a release approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai_engine"))

from jon2_core import generate, load_model
from chat_engine import build_conversation_prompt
from answer_quality import diagnose_answer, validate_generated_answer


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "ai_engine/evaluation/arabic_smoke_tests.json",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-new-chars", type=int, default=180)
    args = parser.parse_args()

    suite = json.loads(args.cases.read_text(encoding="utf-8"))
    if suite.get("format") != "jon2-arabic-human-evaluation-v1":
        raise SystemExit("Unsupported evaluation suite.")
    model, tokenizer, device = load_model(str(args.checkpoint), device="cpu")
    checkpoint_sha = sha256_file(args.checkpoint)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generated = []
    for case in suite["cases"]:
        prompt = build_conversation_prompt(
            case["question"],
            history=[],
            tokenizer=tokenizer,
            context=model.context,
        )
        row = {
            "id": case["id"],
            "dialect": case["dialect"],
            "question": case["question"],
            "human_review_criteria": case["human_review_criteria"],
            "checkpoint_sha256": checkpoint_sha,
            "answer": "",
            "generation_error": None,
            "surface_diagnostics": None,
            "automated_quality_gate": None,
            "human_review": {
                "status": "PENDING",
                "understandable": None,
                "answers_question": None,
                "arabic_fluency": None,
                "factual_or_math_correctness": None,
                "notes": "",
            },
        }
        try:
            full_text = generate(
                model,
                tokenizer,
                prompt,
                device,
                max_new_chars=args.max_new_chars,
                temperature=1.0,
                stop_sequences=["المستخدم:"],
                min_new_tokens=1,
                do_sample=False,
                repetition_penalty=1.10,
                no_repeat_ngram_size=3,
                top_k=0,
            )
            row["answer"] = full_text[len(prompt):].strip()
            row["surface_diagnostics"] = diagnose_answer(row["answer"])
            row["automated_quality_gate"] = validate_generated_answer(row["answer"])
        except Exception as exc:  # retain failed cases in the review report
            row["generation_error"] = f"{type(exc).__name__}: {exc}"
        generated.append(row)

    with args.output.open("w", encoding="utf-8") as handle:
        for row in generated:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Checkpoint SHA-256: {checkpoint_sha}")
    print(f"Prompts: {len(generated)}")
    print(f"Generation errors: {sum(bool(row['generation_error']) for row in generated)}")
    print(f"Surface gate rejected: {sum(row['automated_quality_gate'] is False for row in generated)}")
    print(f"Human review pending: {len(generated)}")
    print(f"Report: {args.output}")
    print("No automated result in this report can approve semantic quality or public release.")


if __name__ == "__main__":
    main()
