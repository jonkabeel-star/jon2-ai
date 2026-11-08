"""Repeatable Arabic checkpoint evaluation for Jon2.

This is a diagnostic harness, not an automatic semantic-quality judge.
Prompts are held out from training and the report explicitly requires human review.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path

import torch

from jon2_core import generate, load_model


PROMPTS = [
    "مرحباً، من أنت؟",
    "اشرح الذكاء الاصطناعي بلغة عربية بسيطة.",
    "ما الفرق بين الطقس والمناخ؟",
    "اكتب ثلاث خطوات لتنظيم الوقت.",
    "لماذا تحتاج النباتات إلى ضوء الشمس؟",
    "حل هذه المسألة: إذا كان معك 12 تفاحة وأعطيت 5، فكم يتبقى؟",
    "اكتب فقرة قصيرة عن التعاون والصداقة.",
    "ما المعلومات التي تحتاجها قبل أن تنصح شخصاً بشراء هاتف؟",
]

def repetition_ratio(text: str, n: int = 3) -> float:
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    if len(words) < n:
        return 0.0
    grams = [tuple(words[i:i+n]) for i in range(len(words)-n+1)]
    return 1.0 - (len(set(grams)) / len(grams))


def evaluate(checkpoint_path: str, max_new_chars: int = 180) -> dict:
    model, tokenizer, device = load_model(checkpoint_path, device="cpu")
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    all_finite = all(torch.isfinite(parameter).all().item() for parameter in model.parameters())
    if not all_finite:
        raise RuntimeError("Checkpoint contains non-finite model parameters.")

    rows = []
    for prompt in PROMPTS:
        answer = generate(
            model, tokenizer, f"المستخدم: {prompt}\nJon2:",
            device, max_new_chars=max_new_chars, do_sample=False,
            repetition_penalty=1.10, no_repeat_ngram_size=3,
            stop_sequences=["المستخدم:", "\nالمستخدم:"],
        )
        answer = answer.split("\nالمستخدم:", 1)[0].strip()
        arabic_letters = sum("\u0600" <= char <= "\u06ff" and char.isalpha() for char in answer)
        visible_chars = sum(not char.isspace() for char in answer)
        rows.append({
            "prompt": prompt,
            "answer": answer,
            "answer_characters": len(answer),
            "arabic_letter_ratio": round(arabic_letters / max(1, visible_chars), 4),
            "trigram_repetition_ratio": round(repetition_ratio(answer), 4),
            "empty": not bool(answer),
            "replacement_character_present": "\ufffd" in answer,
        })

    lengths = [row["answer_characters"] for row in rows]
    repetitions = [row["trigram_repetition_ratio"] for row in rows]
    return {
        "evaluation_version": 1,
        "checkpoint": str(checkpoint_path),
        "device": str(device),
        "model_parameters": parameter_count,
        "all_parameters_finite": all_finite,
        "prompt_count": len(rows),
        "empty_answer_count": sum(row["empty"] for row in rows),
        "replacement_character_count": sum(row["replacement_character_present"] for row in rows),
        "mean_answer_characters": round(statistics.mean(lengths), 2),
        "mean_trigram_repetition_ratio": round(statistics.mean(repetitions), 4),
        "semantic_quality": "HUMAN_REVIEW_REQUIRED",
        "note": (
            "Automatic checks detect empty output, invalid Unicode and simple repetition only. "
            "They do not establish factual accuracy, coherence, instruction following or reasoning."
        ),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Jon2 checkpoint on held-out Arabic prompts.")
    parser.add_argument("--checkpoint", default="ai_engine/checkpoints/jon2-small.pt")
    parser.add_argument("--output", default="training-output/arabic-evaluation.json")
    parser.add_argument("--max-new-chars", type=int, default=180)
    args = parser.parse_args()
    if args.max_new_chars < 1 or args.max_new_chars > 1000:
        parser.error("--max-new-chars must be between 1 and 1000")
    report = evaluate(args.checkpoint, args.max_new_chars)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
