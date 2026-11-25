"""Staged Arabic evaluation: single words, sentences, then multi-turn context.

This is diagnostic only. It never declares semantic success or approves release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import torch

from jon2_core import generate, load_model

SINGLE_WORDS = [
    ("مرحبا", "greeting"),
    ("أهلاً", "greeting"),
    ("شكراً", "gratitude"),
    ("ليه؟", "why_question"),
    ("كم؟", "quantity_question"),
    ("فين؟", "location_question"),
    ("إمتى؟", "time_question"),
    ("ساعدني", "help_request"),
    ("موافق", "agreement"),
    ("لا", "negation"),
    ("نعم", "affirmation"),
    ("كمّل", "continue_request"),
]

SENTENCES = [
    ("msa", "اشرح الفرق بين الحقيقة والرأي في جملتين."),
    ("msa", "إذا كان معك 100 جنيه ودفعت 35، فكم يتبقى؟ وضح الحساب."),
    ("msa", "اذكر خطوتين للتحقق من صحة معلومة قبل نشرها."),
    ("egyptian", "بص، اشرحلي يعني إيه ذكاء اصطناعي بمثال بسيط."),
    ("egyptian", "معايا 250 جنيه واشتريت حاجة بـ175، فاضل كام؟"),
    ("egyptian", "لو مش فاهم درس، أبدأ أذاكره إزاي؟"),
]

CONVERSATIONS = [
    {
        "id": "remember_preference",
        "turns": [
            {"user": "اسمي في المحادثة دي كريم، وبحب الشرح المختصر.", "checks": ["remember_name", "remember_preference"]},
            {"user": "إيه الاسم اللي قلتهولك؟", "checks": ["recall_name"]},
            {"user": "وإزاي بتحب تشرحلي؟", "checks": ["recall_preference"]},
        ],
    },
    {
        "id": "follow_up_context",
        "turns": [
            {"user": "أنا عايز أتعلم Python من الصفر خلال شهر.", "checks": ["goal", "duration"]},
            {"user": "اقترح أول خطوة.", "checks": ["relevant_first_step"]},
            {"user": "كمّل بخطوة تانية مرتبطة بنفس الخطة.", "checks": ["contextual_followup"]},
        ],
    },
]

def _generate(model, tokenizer, device, prompt: str, max_new_chars: int) -> str:
    result = generate(
        model, tokenizer, prompt, device,
        max_new_chars=max_new_chars,
        do_sample=False,
        repetition_penalty=1.10,
        no_repeat_ngram_size=3,
        stop_sequences=["\\nالمستخدم:", "المستخدم:", "\\nJon2:"],
    )
    return result.strip()

def evaluate(checkpoint: str, max_new_chars: int = 160) -> dict:
    model, tokenizer, device = load_model(checkpoint, device="cpu", allow_candidate=True)
    finite = all(torch.isfinite(parameter).all().item() for parameter in model.parameters())
    if not finite:
        raise RuntimeError("Checkpoint contains non-finite parameters.")

    single = []
    for word, intent in SINGLE_WORDS:
        prompt = f"المستخدم: {word}\\nJon2:"
        answer = _generate(model, tokenizer, device, prompt, max_new_chars)
        single.append({"input": word, "expected_intent": intent, "answer": answer, "human_relevance_score": None})

    sentences = []
    for dialect, prompt_text in SENTENCES:
        prompt = f"المستخدم: {prompt_text}\\nJon2:"
        answer = _generate(model, tokenizer, device, prompt, max_new_chars)
        sentences.append({"dialect": dialect, "input": prompt_text, "answer": answer, "human_meaning_score": None, "human_instruction_score": None})

    conversations = []
    for scenario in CONVERSATIONS:
        history = []
        turns = []
        for turn in scenario["turns"]:
            history.append(f"المستخدم: {turn['user']}")
            prompt = "\\n".join(history) + "\\nJon2:"
            answer = _generate(model, tokenizer, device, prompt, max_new_chars)
            turns.append({"user": turn["user"], "answer": answer, "human_context_score": None, "expected_checks": turn["checks"]})
            history.append(f"Jon2: {answer}")
        conversations.append({"scenario": scenario["id"], "turns": turns})

    all_answers = [row["answer"] for row in single + sentences]
    all_answers += [turn["answer"] for scenario in conversations for turn in scenario["turns"]]
    return {
        "format": "jon2-staged-arabic-evaluation-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(Path(checkpoint)),
        "checkpoint_sha256": hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
        "device": str(device),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "parameters_finite": finite,
        "stages": {
            "single_words": {"case_count": len(single), "cases": single},
            "sentences": {"case_count": len(sentences), "cases": sentences},
            "multi_turn_context": {"scenario_count": len(conversations), "scenarios": conversations},
        },
        "automatic_summary": {
            "empty_answers": sum(not answer for answer in all_answers),
            "answer_count": len(all_answers),
            "mean_answer_characters": round(statistics.mean([len(answer) for answer in all_answers]), 2) if all_answers else 0,
        },
        "human_review": {
            "required": True,
            "reviewer": None,
            "review_date": None,
            "single_word_intent_passed": False,
            "sentence_meaning_passed": False,
            "msa_passed": False,
            "egyptian_passed": False,
            "multi_turn_context_passed": False,
            "factuality_passed": False,
            "safety_passed": False,
            "approved_for_release": False,
        },
        "release_gate": "BLOCKED_PENDING_HUMAN_REVIEW",
        "warning": "Automatic output presence is not semantic understanding. This benchmark is diagnostic and not a statistically representative evaluation.",
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Run Jon2 single-word, sentence and context diagnostics.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-new-chars", type=int, default=160)
    args = parser.parse_args()
    if not 1 <= args.max_new_chars <= 1000:
        parser.error("--max-new-chars must be between 1 and 1000")
    report = evaluate(args.checkpoint, args.max_new_chars)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({"checkpoint_sha256": report["checkpoint_sha256"], "stages": {key: value.get("case_count", value.get("scenario_count")) for key, value in report["stages"].items()}, "release_gate": report["release_gate"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
