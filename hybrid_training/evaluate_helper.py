"""Offline evaluation runner for the separate Jon2 helper model.

Uses only a local model directory and a held-out JSONL prompt file.
It does not call a hosted inference API or modify any model weights.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=180)
    args = parser.parse_args()

    if not args.model_dir.is_dir() or not args.prompts.is_file():
        raise FileNotFoundError("A local model directory and held-out prompt file are required.")
    tokenizer = AutoTokenizer.from_pretrained(
        str(args.model_dir), local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(args.model_dir), local_files_only=True, trust_remote_code=False
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.prompts.open("r", encoding="utf-8") as source, args.output.open("w", encoding="utf-8") as sink:
        for line_no, line in enumerate(source, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            prompt_id = item.get("id", f"case-{line_no}")
            messages = item.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError(f"Prompt line {line_no} must contain a non-empty messages array.")
            if any(not isinstance(m, dict) or m.get("role") not in {"system", "user", "assistant"}
                   or not isinstance(m.get("content"), str) or not m["content"].strip()
                   for m in messages):
                raise ValueError(f"Prompt line {line_no} contains invalid message data.")
            if messages[-1]["role"] != "user":
                raise ValueError(f"Prompt line {line_no} must end with a user message.")
            input_ids = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_tensors="pt", enable_thinking=False
            ).to(device)
            with torch.inference_mode():
                generated = model.generate(
                    input_ids=input_ids,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            answer_ids = generated[0, input_ids.shape[-1]:]
            answer = tokenizer.decode(answer_ids, skip_special_tokens=True).strip()
            result = {
                "id": prompt_id,
                "model_dir": str(args.model_dir),
                "messages": messages,
                "answer": answer,
                "human_review": "PENDING",
                "scores": {
                    "meaning": None,
                    "arabic_quality": None,
                    "instruction_following": None,
                    "reasoning": None,
                    "context": None,
                    "honesty_safety": None
                }
            }
            sink.write(json.dumps(result, ensure_ascii=False) + "\n")
            count += 1
    print(json.dumps({
        "status": "evaluation_generated",
        "cases": count,
        "output": str(args.output),
        "device": str(device),
        "human_review_required": True
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
