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


# Authored evaluation-only prompts. Keep this file separate from training corpora.
# These are smoke/diagnostic prompts, not a statistically representative benchmark.
PROMPT_SETS = {
    "msa": [
        "اشرح مفهوم الطاقة المتجددة لطالب في المرحلة الإعدادية، مع مثالين.",
        "ما الفرق بين الحقيقة والرأي؟ وضّح بإيجاز.",
        "اكتب رسالة رسمية قصيرة تطلب فيها تأجيل موعد اجتماع.",
        "إذا قطعت سيارة 180 كيلومتراً في 3 ساعات، فما متوسط سرعتها؟ اشرح الحساب.",
        "اذكر خطوات التحقق من صحة خبر قبل مشاركته.",
        "لخّص أسباب ترشيد استهلاك المياه في فقرة مترابطة.",
        "ما الفرق بين الكتلة والوزن في العلوم؟",
        "اقترح خطة من أربع خطوات لتعلّم مهارة جديدة خلال شهر.",
        "اكتب نهاية بديلة قصيرة لقصة عن تلميذ أعاد محفظة وجدها.",
        "ما البيانات التي ينبغي جمعها قبل مقارنة هاتفين؟",
        "اشرح لماذا لا يثبت الارتباط الإحصائي وحده وجود علاقة سببية.",
        "رتّب هذه المهام حسب الأولوية واذكر سبباً: موعد طبي، واجب غداً، وتنظيف اختياري.",
    ],
    "egyptian": [
        "بص، اشرحلي يعني إيه ذكاء اصطناعي بمثال من حياتنا اليومية.",
        "لو معايا 250 جنيه واشتريت حاجة بـ 175، فاضل كام؟ ووريني الحساب.",
        "عايز أكتب رسالة محترمة أعتذر فيها عن التأخير في الرد.",
        "إيه الفرق بين الموبايل اللي بطاريته كبيرة والموبايل اللي شحنه سريع؟",
        "لو مش فاهم درس، أبدأ أذاكره إزاي من غير ما أتشتت؟",
        "احكيلي موقف قصير عن اتنين صحاب حلّوا مشكلة بالتعاون.",
        "يعني إيه خبر مضلل؟ وإزاي أتأكد إن الكلام اللي على فيسبوك صحيح؟",
        "اقترحلي جدول بسيط أرتب بيه يومي لو عندي شغل ومذاكرة.",
        "لو الأتوبيس بيتأخر كل يوم، إيه معلومات أسجلها عشان أعرف متوسط التأخير؟",
        "إيه الأسئلة اللي أسألها للبائع قبل ما أشتري لابتوب مستعمل؟",
        "اشرحلي ببساطة ليه مينفعش أحكم على منتج من رأي شخص واحد.",
        "اكتب رد قصير ولطيف على حد بيقول لي شكراً على مساعدتك.",
    ],
}

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
    for dialect, prompts in PROMPT_SETS.items():
      for prompt in prompts:
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
            "dialect": dialect,
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
    dialect_summary = {
        dialect: {
            "prompt_count": sum(row["dialect"] == dialect for row in rows),
            "empty_answer_count": sum(row["dialect"] == dialect and row["empty"] for row in rows),
            "mean_answer_characters": round(statistics.mean(
                [row["answer_characters"] for row in rows if row["dialect"] == dialect]
            ), 2),
        }
        for dialect in PROMPT_SETS
    }
    return {
        "evaluation_version": 2,
        "checkpoint": str(checkpoint_path),
        "device": str(device),
        "model_parameters": parameter_count,
        "all_parameters_finite": all_finite,
        "prompt_count": len(rows),
        "dialect_summary": dialect_summary,
        "empty_answer_count": sum(row["empty"] for row in rows),
        "replacement_character_count": sum(row["replacement_character_present"] for row in rows),
        "mean_answer_characters": round(statistics.mean(lengths), 2),
        "mean_trigram_repetition_ratio": round(statistics.mean(repetitions), 4),
        "semantic_quality": "HUMAN_REVIEW_REQUIRED",
        "human_review": {
            "required": True,
            "reviewed_by": None,
            "reviewed_at": None,
            "msa_cases_scored": 0,
            "egyptian_cases_scored": 0,
            "factuality_passed": False,
            "coherence_passed": False,
            "instruction_following_passed": False,
            "safety_passed": False,
            "approved_for_release": False,
        },
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
