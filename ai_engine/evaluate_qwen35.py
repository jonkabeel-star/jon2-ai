#!/usr/bin/env python3
"""Strict, free-GPU-only Qwen3.5-9B evaluation against Jon2's held-out Arabic benchmark.

Evaluation only: this script never trains, fine-tunes, uploads, or changes Jon2 weights.
It requires a real CUDA GPU and 4-bit bitsandbytes loading. It fails closed on CPU.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai_engine.jon2_inference import (\n    max_new_tokens_for, with_jon2_system_prompt, classify_finish_reason,\n    sanitize_safety_answer,\n)

MODEL_ID = "Qwen/Qwen3.5-9B"
DEFAULT_BENCHMARK = Path(__file__).parent / "evaluation" / "egyptian_arabic_prompts.jsonl"


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"Invalid record at line {line_number}")
            record_id = item.get("id")
            if not isinstance(record_id, str) or not record_id.strip() or record_id in seen:
                raise ValueError(f"Missing/duplicate id at line {line_number}")
            if ("prompt" in item) == ("turns" in item):
                raise ValueError(f"{record_id} must contain exactly one of prompt or turns")
            if "prompt" in item and (not isinstance(item["prompt"], str) or not item["prompt"].strip()):
                raise ValueError(f"Invalid prompt in {record_id}")
            if "turns" in item:
                turns = item["turns"]
                if not isinstance(turns, list) or len(turns) < 2:
                    raise ValueError(f"Invalid turns in {record_id}")
                for turn in turns:
                    if not isinstance(turn, dict) or turn.get("role") not in {"system", "user", "assistant"}:
                        raise ValueError(f"Invalid turn role in {record_id}")
                    if not isinstance(turn.get("content"), str) or not turn["content"].strip():
                        raise ValueError(f"Invalid turn content in {record_id}")
                if turns[-1]["role"] != "user":
                    raise ValueError(f"Last turn must be user in {record_id}")
            seen.add(record_id)
            records.append(item)
    if not records:
        raise ValueError("Benchmark contains no records")
    return records


def to_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    if "turns" in item:
        return [{"role": turn["role"], "content": turn["content"]} for turn in item["turns"]]
    return [{"role": "user", "content": item["prompt"]}]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=Path("qwen35_9b_egyptian_trial.jsonl"))
    parser.add_argument("--limit", type=int, default=0, help="0 runs all held-out cases")
    parser.add_argument("--max-new-tokens", type=int, default=None, help="Optional override; task-specific budgets are used by default")
    parser.add_argument("--max-input-tokens", type=int, default=4096)
    args = parser.parse_args()
    if (args.max_new_tokens is not None and args.max_new_tokens < 1) or args.max_input_tokens < 128:
        parser.error("token limits are too small or invalid")

    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required. CPU fallback is disabled; no evaluation was run.")
    if torch.cuda.device_count() < 1:
        raise RuntimeError("No CUDA device detected.")

    try:
        from transformers import AutoTokenizer, Qwen3_5ForCausalLM, BitsAndBytesConfig
        import bitsandbytes  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Install current Transformers and bitsandbytes in the Kaggle GPU notebook first."
        ) from exc

    records = load_records(args.benchmark)
    if args.limit:
        records = records[: args.limit]

    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"Loading {MODEL_ID} in 4-bit NF4. This downloads public model weights once.")
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=False)
    model = Qwen3_5ForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        trust_remote_code=False,
        attn_implementation="sdpa",
    )
    model.eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for index, item in enumerate(records, start=1):
            result: dict[str, Any] = {
                "id": item["id"],
                "model": MODEL_ID,
                "split": item.get("split", "held_out"),
                "training_use": False,
                "status": "error",
                "answer": "",
                "messages": [],
                "finish_reason": "error",
                "generated_tokens": 0,
                "input_tokens": 0,
                "max_new_tokens": 0,
            }
            try:
                messages = with_jon2_system_prompt(to_messages(item))
                result["messages"] = messages
                result["question"] = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
                inputs = tokenizer(text=[prompt], return_tensors="pt", truncation=False)
                if inputs["input_ids"].shape[-1] > args.max_input_tokens:
                    raise ValueError("Input exceeds configured token limit; prompt was not truncated.")
                input_device = model.get_input_embeddings().weight.device
                inputs = {key: value.to(input_device) for key, value in inputs.items()}
                token_budget = max_new_tokens_for(item["id"], args.max_new_tokens)
                result["input_tokens"] = int(inputs["input_ids"].shape[-1])
                result["max_new_tokens"] = token_budget
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs,
                        max_new_tokens=token_budget,
                        do_sample=False,
                        repetition_penalty=1.05,
                    )
                new_tokens = generated[:, inputs["input_ids"].shape[-1]:]
                generated_count = int(new_tokens.shape[-1])
                last_token_id = int(new_tokens[0, -1].item()) if generated_count else None
                eos_ids = model.generation_config.eos_token_id
                if eos_ids is None:
                    eos_ids = tokenizer.eos_token_id
                finish_reason = classify_finish_reason(
                    generated_count, token_budget, last_token_id, eos_ids
                )
                result["generated_tokens"] = generated_count
                result["finish_reason"] = finish_reason
                answer = tokenizer.batch_decode(
                    new_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0].strip()
                answer = sanitize_safety_answer(answer, item["id"])
                result["answer"] = answer
                result["status"] = (
                    "empty_output" if not answer else
                    "truncated" if finish_reason == "length" else "ok"
                )
                result["review_criteria"] = item.get("review_criteria", "")
            except Exception as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(
                f"[{index}/{len(records)}] {item['id']}: {result['status']} "
                f"(finish={result['finish_reason']}, tokens={result['generated_tokens']}/"
                f"{result['max_new_tokens']})"
            )

    print(f"Raw evaluation saved to {args.output}")
    print("Evaluation only. No fine-tuning, training, checkpoint changes, or release approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
