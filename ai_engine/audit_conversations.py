"""Read-only audit for structured Jon2 multi-turn conversation JSONL files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from conversation_context import audit_conversations, load_conversations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit dialogue depth, alternation, and exact duplicate conversations."
    )
    parser.add_argument(
        "--data",
        default="ai_engine/training_data/dialogue/jon2_dialogue_multiturn_stage2.jsonl",
        help="Path to a JSONL conversation file; no files are modified.",
    )
    parser.add_argument("--output", default="", help="Optional JSON report path.")
    args = parser.parse_args()

    conversations = load_conversations(Path(args.data))
    report = {
        "audit_type": "jon2_multiturn_conversation_structure",
        "source_file": str(Path(args.data)),
        **audit_conversations(conversations),
        "notice": (
            "Structural validity and multi-turn counts do not establish answer correctness, "
            "coherence, factuality, data rights, or training approval."
        ),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
