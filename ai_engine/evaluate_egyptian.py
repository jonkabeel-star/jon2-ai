"""Run a human-review benchmark on Jon2's original checkpoint.

Supports both single-turn prompts and real multi-turn conversations. No hosted
model/API is used, and failed generations remain explicit failures.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def load_benchmark_cases(path: Path) -> list[dict]:
    cases = []
    seen = set()
    required = {"id", "review_criteria", "split", "language"}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Invalid benchmark record at line {line_number}")
        if item["split"] != "held_out" or item["language"] != "Egyptian Arabic":
            raise ValueError(f"Benchmark record {item.get('id')} has invalid split/language metadata")
        if not isinstance(item["id"], str) or not item["id"].strip() or item["id"] in seen:
            raise ValueError(f"Missing or duplicate benchmark id at line {line_number}")
        prompt_present = "prompt" in item
        turns_present = "turns" in item
        if prompt_present == turns_present:
            raise ValueError(
                f"Record {item['id']} must contain exactly one of prompt or turns"
            )
        has_prompt = prompt_present and isinstance(item.get("prompt"), str) and bool(item["prompt"].strip())
        turns = item.get("turns")
        has_turns = (
            isinstance(turns, list) and len(turns) >= 2
            and all(
                isinstance(turn, dict)
                and turn.get("role") in {"user", "assistant"}
                and isinstance(turn.get("content"), str)
                and turn["content"].strip()
                for turn in turns
            )
            and any(turn["role"] == "user" for turn in turns)
            and turns[-1]["role"] == "user"
        )
        if has_prompt == has_turns:
            raise ValueError(
                f"Record {item['id']} must contain exactly one of prompt or valid turns"
            )
        seen.add(item["id"])
        cases.append(item)
    if not cases:
        raise ValueError("The Egyptian Arabic benchmark is empty.")
    return cases


def run_case(chat_engine, item: dict) -> dict:
    if "turns" not in item:
        return {
            "answer": chat_engine.generate_reply(item["prompt"]),
            "conversation": [{"role": "user", "content": item["prompt"]}],
        }

    history = []
    answer = None
    for turn in item["turns"]:
        if turn["role"] == "assistant":
            history.append({"role": "assistant", "content": turn["content"]})
            continue
        answer = chat_engine.generate_reply(turn["content"], history=history)
        history.extend([
            {"role": "user", "content": turn["content"]},
            {"role": "assistant", "content": answer},
        ])
    return {"answer": answer, "conversation": history}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate an original Jon2 checkpoint on held-out Egyptian Arabic prompts."
    )
    parser.add_argument("--checkpoint", required=True, help="Path to a private Jon2 .pt checkpoint.")
    parser.add_argument("--prompts", default=str(HERE / "evaluation" / "egyptian_arabic_prompts.jsonl"))
    parser.add_argument("--output", default="jon2-egyptian-arabic-review.jsonl")
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint).expanduser()
    prompts_path = Path(args.prompts)
    output_path = Path(args.output)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    if not prompts_path.is_file():
        raise FileNotFoundError(f"Prompt set not found: {prompts_path}")

    cases = load_benchmark_cases(prompts_path)
    os.environ["JON2_CHECKPOINT"] = str(checkpoint.resolve())
    import chat_engine
    from answer_quality import diagnose_answer

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for index, item in enumerate(cases, 1):
            record = {
                "id": item["id"],
                "review_criteria": item["review_criteria"],
                "language": item["language"],
                "checkpoint": str(checkpoint.resolve()),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                result = run_case(chat_engine, item)
                answer = result["answer"]
                record.update({
                    "status": "generated",
                    "answer": answer,
                    "conversation": result["conversation"],
                    "surface_diagnostics": diagnose_answer(answer),
                })
            except Exception as exc:
                record.update({
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                })
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"[{index}/{len(cases)}] {item['id']}: {record['status']}")
    print(f"Saved {len(cases)} real inference records to {output_path}")
    print("Surface diagnostics are not semantic scores. Human review is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
