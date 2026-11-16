"""Run a human-review benchmark on Jon2's original checkpoint using Egyptian Arabic prompts.

This tool records real model output. It does not manufacture answers or decide
semantic quality automatically. Keep the resulting report private.
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate an original Jon2 checkpoint on held-out Egyptian Arabic prompts.")
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

    # chat_engine reads this variable when imported; no external service is used.
    os.environ["JON2_CHECKPOINT"] = str(checkpoint.resolve())
    import chat_engine
    from answer_quality import diagnose_answer

    cases = []
    seen = set()
    for line_number, line in enumerate(prompts_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        required = {"id", "prompt", "review_criteria", "split", "language"}
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Invalid benchmark record at line {line_number}")
        if item["split"] != "held_out" or item["language"] != "Egyptian Arabic":
            raise ValueError(f"Benchmark record {item.get('id')} has invalid split/language metadata")
        if item["id"] in seen:
            raise ValueError(f"Duplicate benchmark id: {item['id']}")
        seen.add(item["id"])
        cases.append(item)
    if not cases:
        raise ValueError("The Egyptian Arabic benchmark is empty.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for item in cases:
            record = {
                "id": item["id"],
                "prompt": item["prompt"],
                "review_criteria": item["review_criteria"],
                "language": item["language"],
                "checkpoint": str(checkpoint.resolve()),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                answer = chat_engine.generate_reply(item["prompt"])
                record["status"] = "generated"
                record["answer"] = answer
                record["surface_diagnostics"] = diagnose_answer(answer)
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = f"{type(exc).__name__}: {exc}"
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
            print(f"[{count}/{len(cases)}] {item['id']}: {record['status']}")
    print(f"Saved {count} real inference records to {output_path}")
    print("IMPORTANT: Surface diagnostics are not semantic scores. Human review is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
