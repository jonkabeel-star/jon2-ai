"""Run the single-word Arabic benchmark against the original Jon2 checkpoint.

Run from ai_engine/: python -m evaluations.run_single_word_eval
This records raw generations for human review; it never marks the model approved.
"""
from __future__ import annotations

import json
from pathlib import Path

from answer_quality import diagnose_answer, validate_generated_answer
from chat_engine import generate_raw_reply

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "single_word_arabic_v1.json"
OUTPUT = ROOT / "single_word_arabic_v1.results.json"


def main() -> int:
    benchmark = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in benchmark["cases"]:
        try:
            answer = generate_raw_reply(
                case["message"],
                history=case.get("history", []),
            )
            results.append({
                "id": case["id"],
                "message": case["message"],
                "intent": case["intent"],
                "answer": answer,
                "surface_valid": validate_generated_answer(answer),
                "diagnostics": diagnose_answer(answer),
                "human_review": "pending",
            })
        except Exception as error:
            results.append({
                "id": case["id"],
                "message": case["message"],
                "intent": case["intent"],
                "answer": "",
                "surface_valid": False,
                "error_type": type(error).__name__,
                "human_review": "failed_generation",
            })

    report = {
        "benchmark": benchmark["benchmark"],
        "model": "Jon2 Original Transformer",
        "results_count": len(results),
        "surface_valid_count": sum(item["surface_valid"] for item in results),
        "semantic_quality_approved": False,
        "release_approved": False,
        "results": results,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "benchmark": report["benchmark"],
        "results_count": report["results_count"],
        "surface_valid_count": report["surface_valid_count"],
        "report_path": str(OUTPUT),
        "semantic_quality_approved": False,
        "release_approved": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
