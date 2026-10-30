"""Run a repeatable, human-reviewable Arabic smoke evaluation of Jon2.

This is not an automatic measure of intelligence or factual accuracy. It
prints unseen prompts and generated answers so a reviewer can score them.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import torch

from jon2_core import generate, load_model


TEST_PROMPTS = [
    "المستخدم: اشرح الفرق بين الطقس والمناخ في جملتين.\nJon2:",
    "المستخدم: إذا كان ثمن كتاب 120 جنيهًا وخصمه 25 بالمئة، فما السعر بعد الخصم؟ وضح الحساب.\nJon2:",
    "المستخدم: اكتب قصة قصيرة من أربعة أحداث مترابطة عن طفل يساعد جاره.\nJon2:",
    "المستخدم: ما المعلومات التي تحتاجها قبل أن تنصحني بشراء هاتف؟\nJon2:",
    "المستخدم: هل تستطيع تأكيد سعر الدولار الآن؟\nJon2:",
    "المستخدم: اشرح معنى النسخ الاحتياطي لشخص مبتدئ.\nJon2:",
    "المستخدم: ما الفرق بين الحقيقة والرأي؟ أعطني مثالًا.\nJon2:",
    "المستخدم: اكتب ردًا مهذبًا على شخص اختلف معي في الرأي.\nJon2:",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Human-review smoke test for Jon2.")
    parser.add_argument(
        "--checkpoint",
        default=str(Path(__file__).resolve().parent / "checkpoints" / "jon2-small.pt"),
    )
    parser.add_argument("--max-new-chars", type=int, default=240)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if args.max_new_chars <= 0:
        parser.error("--max-new-chars must be positive")
    if args.temperature <= 0:
        parser.error("--temperature must be positive")

    checkpoint = Path(args.checkpoint)
    if not checkpoint.is_file():
        print(
            "لا يوجد checkpoint مدرّب لـ Jon2 حتى الآن. "
            f"المسار المتوقع: {checkpoint}"
        )
        return 2

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    model, tokenizer, device = load_model(str(checkpoint))
    results = []
    for prompt in TEST_PROMPTS:
        full = generate(
            model,
            tokenizer,
            prompt,
            device,
            max_new_chars=args.max_new_chars,
            temperature=args.temperature,
        )
        answer = full[len(prompt):].strip()
        item = {"prompt": prompt, "answer": answer}
        results.append(item)
        print("\n" + "=" * 72)
        print(prompt)
        print(answer or "[لم ينتج النموذج إجابة]")

    report = {
        "model": "Jon2 Original Transformer",
        "checkpoint": str(checkpoint),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "temperature": args.temperature,
        "max_new_chars": args.max_new_chars,
        "review_note": (
            "Human review required. This smoke test does not establish factual "
            "accuracy, general capability, safety, or production readiness."
        ),
        "results": results,
    }
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nSaved review report: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
