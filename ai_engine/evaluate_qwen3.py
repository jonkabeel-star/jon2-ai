#!/usr/bin/env python3
"""Run an isolated Qwen3 Arabic trial against Jon2's held-out benchmark.

This script does not train, fine-tune, modify, or replace Jon2 checkpoints.
It downloads/loads the public Qwen3-0.6B weights into the current runtime and
writes raw model outputs for human review. Do not feed this benchmark to training.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL = "Qwen/Qwen3-0.6B"
DEFAULT_BENCHMARK = Path(__file__).parent / "evaluation" / "egyptian_arabic_prompts.jsonl"


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or not item.get("id"):
                raise ValueError(f"Invalid benchmark record at line {line_number}")
            if not (item.get("prompt") or item.get("turns")):
                raise ValueError(f"Record has no prompt/turns at line {line_number}")
            records.append(item)
    if not records:
        raise ValueError("Benchmark contains no records")
    return records


def record_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    if item.get("turns"):
        turns = item["turns"]
        if not isinstance(turns, list):
            raise ValueError(f"turns must be a list for {item['id']}")
        messages = []
        for turn in turns:
            role, content = turn.get("role"), turn.get("content")
            if role not in {"user", "assistant", "system"} or not isinstance(content, str):
                raise ValueError(f"Invalid turn in {item['id']}")
            messages.append({"role": role, "content": content})
        if not messages or messages[-1]["role"] != "user":
            raise ValueError(f"Last turn must be user for {item['id']}")
        return messages
    return [{"role": "user", "content": item["prompt"]}]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=Path("qwen3_egyptian_trial.jsonl"))
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--limit", type=int, default=0, help="Optional smoke-test limit; 0 runs all records.")
    args = parser.parse_args()

    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")

    records = load_records(args.benchmark)
    if args.limit:
        records = records[: args.limit]

    print(f"Loading {args.model}; this may download model weights on first run.")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=False,
    )
    model.eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for index, item in enumerate(records, start=1):
            messages = record_messages(item)
            try:
                try:
                    prompt_text = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                        enable_thinking=False,
                    )
                except TypeError:
                    # Compatibility with Transformers versions whose chat-template
                    # method does not expose enable_thinking.
                    prompt_text = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True,
                    )

                inputs = tokenizer(prompt_text, return_tensors="pt")
                input_device = model.get_input_embeddings().weight.device
                inputs = {key: value.to(input_device) for key, value in inputs.items()}
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=args.max_new_tokens,
                        do_sample=False,
                        repetition_penalty=1.08,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                new_tokens = generated[0, inputs["input_ids"].shape[1] :]
                answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                result = {
                    "id": item["id"],
                    "model": args.model,
                    "answer": answer,
                    "review_criteria": item.get("review_criteria", ""),
                    "status": "ok" if answer else "empty_output",
                    "split": item.get("split", "held_out"),
                    "training_use": False,
                }
            except Exception as exc:  # Preserve failures; never fabricate a reply.
                result = {
                    "id": item["id"],
                    "model": args.model,
                    "answer": "",
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "review_criteria": item.get("review_criteria", ""),
                    "split": item.get("split", "held_out"),
                    "training_use": False,
                }
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()
            print(f"[{index}/{len(records)}] {item['id']}: {result['status']}")

    print(f"Saved raw trial outputs to: {args.output}")
    print("No checkpoint was trained, changed, or promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
