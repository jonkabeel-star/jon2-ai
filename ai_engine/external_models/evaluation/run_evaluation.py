"""Run the owner-authored Jon2 Arabic evaluation suite against a local checkpoint.

No network access, dataset download, or hosted inference is performed by this script.
It writes evaluation results locally; never commit private outputs or model weights.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MODEL_ADAPTER_DIR = HERE.parent
sys.path.insert(0, str(MODEL_ADAPTER_DIR))

import jais2_runtime  # noqa: E402

SUITE_PATH = HERE / "jon2_arabic_eval_v1.json"


def load_suite() -> dict[str, Any]:
    with SUITE_PATH.open("r", encoding="utf-8") as handle:
        suite = json.load(handle)
    if not isinstance(suite.get("conversations"), list) or not suite["conversations"]:
        raise ValueError("Evaluation suite must contain a non-empty conversations list.")
    seen: set[str] = set()
    for conversation in suite["conversations"]:
        case_id = conversation.get("id")
        turns = conversation.get("turns")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("Each conversation needs a unique non-empty id.")
        seen.add(case_id)
        if not isinstance(turns, list) or not turns:
            raise ValueError(f"{case_id}: turns must be a non-empty list.")
        for turn in turns:
            if not isinstance(turn, dict) or not isinstance(turn.get("user"), str) or not turn["user"].strip():
                raise ValueError(f"{case_id}: every turn must contain a non-empty user string.")
    return suite


def run_evaluation(suite: dict[str, Any], output_path: Path, max_new_tokens: int) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for conversation in suite["conversations"]:
        history: list[dict[str, str]] = []
        turn_results: list[dict[str, str]] = []
        for index, turn in enumerate(conversation["turns"], start=1):
            prompt = turn["user"].strip()
            reply = jais2_runtime.generate_reply(
                prompt,
                history,
                max_new_tokens=max_new_tokens,
            )
            turn_results.append({"turn": str(index), "prompt": prompt, "reply": reply})
            history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": reply},
            ])
        results.append({
            "id": conversation["id"],
            "category": conversation.get("category", "uncategorized"),
            "turns": turn_results,
        })

    report = {
        "suite_name": suite["suite_name"],
        "suite_version": suite["suite_version"],
        "model_id": jais2_runtime.MODEL_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "local_checkpoint_only",
        "automatic_quality_score": None,
        "human_review_required": True,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or run Jon2's local Arabic evaluation suite.")
    parser.add_argument("--validate-only", action="store_true", help="Validate the suite without loading a model.")
    parser.add_argument("--output", type=Path, default=HERE / "local_eval_results.json")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()

    suite = load_suite()
    total_turns = sum(len(item["turns"]) for item in suite["conversations"])
    print(f"Suite valid: {len(suite['conversations'])} conversations, {total_turns} user turns.")
    if args.validate_only:
        print("Validation only: no model loaded and no inference performed.")
        return 0

    if not os.getenv("JON2_JAIS2_LOCAL_PATH", "").strip():
        print("STOP: set JON2_JAIS2_LOCAL_PATH to a rights-approved local checkpoint first.", file=sys.stderr)
        return 2
    report = run_evaluation(suite, args.output, args.max_new_tokens)
    print(f"Saved {len(report['results'])} conversation results to: {args.output}")
    print("No automatic quality score is produced. Human review is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
