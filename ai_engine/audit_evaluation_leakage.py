"""Read-only exact-prompt leakage audit for Jon2 held-out Arabic evaluations."""
from __future__ import annotations
import argparse
import json
import re
import unicodedata
from pathlib import Path
from corpus_reader import read_corpus

DEFAULT_EVALUATION_FILES = (
    Path("ai_engine/evaluation/prompts_ar.jsonl"),
    Path("ai_engine/evaluation/prompts_egyptian_ar.jsonl"),
)

def normalize_prompt(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()

def load_evaluation_prompts(paths: list[Path]) -> list[dict]:
    prompts, seen_ids = [], set()
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid evaluation JSONL {path}:{line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Invalid evaluation record {path}:{line_number}: expected object")
            prompt_id, prompt = record.get("id"), record.get("prompt")
            if not isinstance(prompt_id, str) or not prompt_id.strip():
                raise ValueError(f"Invalid evaluation record {path}:{line_number}: missing id")
            if prompt_id in seen_ids:
                raise ValueError(f"Duplicate evaluation prompt id: {prompt_id}")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"Invalid evaluation record {path}:{line_number}: missing prompt")
            seen_ids.add(prompt_id)
            prompts.append({"id": prompt_id, "prompt": prompt, "source": str(path)})
    return prompts

def audit_overlap(training_dir: Path, evaluation_files: list[Path], include_jsonl: bool = False) -> dict:
    corpus = read_corpus(training_dir, include_jsonl=include_jsonl)
    normalized_corpus = normalize_prompt(corpus)
    prompts = load_evaluation_prompts(evaluation_files)
    matches = [
        {"id": item["id"], "source": item["source"]}
        for item in prompts
        if normalize_prompt(item["prompt"]) in normalized_corpus
    ]
    return {
        "status": "OVERLAP_FOUND" if matches else "NO_EXACT_PROMPT_OVERLAP",
        "training_directory": str(training_dir),
        "training_jsonl_included": include_jsonl,
        "evaluation_prompt_count": len(prompts),
        "exact_normalized_prompt_matches": matches,
        "limitations": [
            "Detects exact normalized full-prompt copies only.",
            "Does not detect paraphrases, partial overlap, or semantic contamination.",
            "A clean result is not proof of complete train/evaluation independence.",
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit exact held-out prompt overlap without modifying data.")
    parser.add_argument("--data", type=Path, default=Path("ai_engine/training_data"))
    parser.add_argument("--evaluation", type=Path, action="append", dest="evaluation_files")
    parser.add_argument("--include-jsonl", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_overlap(args.data, args.evaluation_files or list(DEFAULT_EVALUATION_FILES), args.include_jsonl)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if report["exact_normalized_prompt_matches"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
