"""Run a six-capability Arabic benchmark against Qwen3.5 or a private Jon2 LoRA adapter.

This produces raw model answers and a human-review CSV. Automated diagnostics are
not a semantic quality verdict and never enable public release.
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
import torch


def load_model(model_id: str, adapter_dir: str | None):
    from transformers import AutoTokenizer, BitsAndBytesConfig, Qwen3_5ForCausalLM
    from peft import PeftModel
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=False)
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16,
    )
    model = Qwen3_5ForCausalLM.from_pretrained(
        model_id, quantization_config=quant, device_map={"": 0},
        torch_dtype=torch.float16, low_cpu_mem_usage=True,
        trust_remote_code=False, attn_implementation="sdpa",
    )
    if adapter_dir:
        model = PeftModel.from_pretrained(model, adapter_dir, is_trainable=False)
    model.eval()
    return tokenizer, model


def surface_diagnostics(text: str) -> dict:
    words = re.findall(r"\S+", text)
    arabic_words = [w for w in words if re.search(r"[\u0600-\u06ff]", w)]
    short = sum(1 for w in arabic_words if len(re.sub(r"[^\u0600-\u06ff]", "", w)) <= 2)
    fragmented = bool(arabic_words) and short / max(1, len(arabic_words)) > 0.48
    return {
        "empty": not bool(text.strip()),
        "repeated_4gram": any(
            " ".join(words[i:i+4]) == " ".join(words[j:j+4])
            for i in range(len(words)) for j in range(i+4, len(words)-3)
        ),
        "fragmented_surface_suspected": fragmented,
        "word_count": len(words),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model-id", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--adapter-dir", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required; CPU fallback is disabled.")
    tests = json.loads(args.tests.read_text(encoding="utf-8"))
    if not isinstance(tests, list) or not tests:
        raise ValueError("Benchmark file must be a non-empty JSON array.")
    if args.limit:
        tests = tests[:args.limit]
    ids = [item.get("id") for item in tests]
    if len(set(ids)) != len(ids) or any(not x for x in ids):
        raise ValueError("Every benchmark case needs a unique non-empty id.")
    tokenizer, model = load_model(args.model_id, args.adapter_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    review_path = args.output.with_suffix(".human_review.csv")
    with args.output.open("w", encoding="utf-8") as raw, review_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as review:
        writer = csv.DictWriter(review, fieldnames=[
            "id", "capability", "language", "prompt", "answer",
            "rubric", "reviewer_1_score_0_4", "reviewer_1_notes",
            "reviewer_2_score_0_4", "reviewer_2_notes", "adjudicated_score_0_4",
        ])
        writer.writeheader()
        for index, case in enumerate(tests, start=1):
            messages = case.get("messages")
            if not isinstance(messages, list) or not messages or messages[-1].get("role") != "user":
                raise ValueError(f"{case.get('id')}: messages must end with a user turn.")
            encoded = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt", enable_thinking=False,
            ).to(model.device)
            with torch.inference_mode():
                generated = model.generate(
                    **encoded, max_new_tokens=args.max_new_tokens,
                    do_sample=False, repetition_penalty=1.05,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            new_tokens = generated[:, encoded["input_ids"].shape[1]:]
            answer = tokenizer.decode(
                new_tokens[0], skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            ).strip()
            result = {
                "id": case["id"], "capability": case["capability"],
                "language": case.get("language", "ar"),
                "messages": messages, "answer": answer,
                "rubric": case.get("rubric", []),
                "surface_diagnostics": surface_diagnostics(answer),
                "model_id": args.model_id,
                "adapter_dir": args.adapter_dir,
                "human_review_required": True,
            }
            raw.write(json.dumps(result, ensure_ascii=False) + "\n")
            writer.writerow({
                "id": case["id"], "capability": case["capability"],
                "language": case.get("language", "ar"),
                "prompt": messages[-1]["content"], "answer": answer,
                "rubric": " | ".join(case.get("rubric", [])),
                "reviewer_1_score_0_4": "", "reviewer_1_notes": "",
                "reviewer_2_score_0_4": "", "reviewer_2_notes": "",
                "adjudicated_score_0_4": "",
            })
            print(f"[{index}/{len(tests)}] {case['id']} | {case['capability']} | {len(answer)} chars")
    print(f"Raw results: {args.output}")
    print(f"Human review sheet: {review_path}")
    print("No automated score or release decision was produced.")


if __name__ == "__main__":
    main()
