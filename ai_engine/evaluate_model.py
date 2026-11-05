"""Generate a human-reviewable report from a trained Jon2 checkpoint.

Evaluation prompts are held out as JSONL and are not part of the .txt training
corpus. This tool never assigns quality scores or approves a model automatically.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch

from jon2_core import generate, load_model

REVIEW_DIMENSIONS = (
    "correctness",
    "relevance",
    "arabic_quality",
    "coherence",
    "uncertainty",
    "instruction_following",
)


def load_prompts(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation prompt file not found: {path}")
    prompts = []
    seen_ids = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on evaluation line {line_number}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation line {line_number} must be a JSON object.")
        prompt_id, prompt = item.get("id"), item.get("prompt")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ValueError(f"Evaluation line {line_number} needs a non-empty string id.")
        if prompt_id in seen_ids:
            raise ValueError(f"Duplicate evaluation prompt id: {prompt_id}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Evaluation prompt {prompt_id} needs non-empty prompt text.")
        seen_ids.add(prompt_id)
        prompts.append({"id": prompt_id, "prompt": prompt.strip()})
    if not prompts:
        raise ValueError("Evaluation set is empty.")
    return prompts


def diagnose_answer(answer: str) -> dict:
    """Report surface-level warning signals without pretending to judge meaning."""
    import re

    text = answer.strip() if isinstance(answer, str) else ""
    words = re.findall(r"\\S+", text)
    visible = [char for char in text if not char.isspace()]
    arabic = len(re.findall(r"[\\u0621-\\u064A\\u066E-\\u06D3]", text))
    unique_ratio = len(set(words)) / max(1, len(words))
    repeated_trigram = any(
        words[index:index + 3] == words[index + 3:index + 6]
        for index in range(max(0, len(words) - 5))
    )
    warnings = []
    if len(text) < 20:
        warnings.append("very_short_answer")
    if len(words) < 4:
        warnings.append("very_few_words")
    if arabic / max(1, len(visible)) < 0.70:
        warnings.append("low_arabic_character_ratio")
    if len(words) >= 8 and unique_ratio < 0.45:
        warnings.append("low_unique_word_ratio")
    if repeated_trigram:
        warnings.append("repeated_three_word_sequence")
    if not text:
        warnings.append("empty_answer")
    return {
        "character_count": len(text),
        "word_count": len(words),
        "arabic_character_ratio": round(arabic / max(1, len(visible)), 3),
        "unique_word_ratio": round(unique_ratio, 3),
        "surface_warnings": warnings,
        "human_semantic_review_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a held-out human-review report for a trained Jon2 checkpoint."
    )
    parser.add_argument(
        "--checkpoint",
        default=str(Path(__file__).resolve().parent / "checkpoints" / "jon2-small.pt"),
    )
    parser.add_argument(
        "--prompts",
        default=str(Path(__file__).resolve().parent / "evaluation" / "prompts_ar.jsonl"),
    )
    parser.add_argument(
        "--max-new-chars",
        type=int,
        default=180,
    )
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "evaluation" / "review-report.json"),
    )
    parser.add_argument("--device", default=None, help="Optional torch device, e.g. cpu or cuda")
    args = parser.parse_args()

    if args.max_new_chars <= 0 or args.temperature <= 0:
        parser.error("max-new-chars and temperature must be positive")

    checkpoint = Path(args.checkpoint)
    if not checkpoint.is_file():
        print(
            "لا يوجد checkpoint مدرّب لـ Jon2 حتى الآن. "
            f"المسار المتوقع: {checkpoint}"
        )
        return 2

    prompts = load_prompts(Path(args.prompts))
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    model, tokenizer, device = load_model(str(checkpoint), device=args.device)
    results = []
    for item in prompts:
        prompt_text = f"المستخدم: {item['prompt']}\nJon2:"
        full = generate(
            model,
            tokenizer,
            prompt_text,
            device,
            max_new_chars=args.max_new_chars,
            temperature=args.temperature,
            stop_sequences=["المستخدم:"],
        )
        answer = full[len(prompt_text):].strip()
        results.append({
            "id": item["id"],
            "prompt": item["prompt"],
            "generated_answer": answer,
            "human_review": {
                "reviewed": False,
                "reviewer": None,
                "review_date": None,
                "scores": {dimension: None for dimension in REVIEW_DIMENSIONS},
                "notes": "",
            },
        })
        print("\n" + "=" * 72)
        print(item["id"] + ": " + item["prompt"])
        print(answer or "[لم ينتج النموذج إجابة]")

    report = {
        "project": "Jon2 AI",
        "evaluation_type": "human_review_required",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(checkpoint),
        "device": str(device),
        "seed": args.seed,
        "temperature": args.temperature,
        "max_new_chars": args.max_new_chars,
        "prompt_count": len(results),
        "automated_quality_verdict": None,\n        "diagnostic_notice": (\n            "Surface warnings detect empty, unusually short, low-Arabic, or repetitive text only. " \n            "They do not measure correctness, relevance, coherence, or factuality and never approve release."\n        ),
        "release_approved": False,
        "results": results,
        "notice": (
            "Generated answers are not a quality pass. A human reviewer must "
            "score each answer using EVALUATION_RUBRIC.md. This report does not "
            "prove factuality, safety, privacy, or training-data rights."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    print(f"\nGenerated {len(results)} answers for human review.")
    print(f"Review report: {output}")
    print("No automatic quality score or release approval was assigned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
