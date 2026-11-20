#!/usr/bin/env python3
"""Export a private, checkpoint-bound Python reference for Safari parity testing.

The checkpoint and generated reference stay local. Never commit either file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai_engine"))

import torch
from jon2_core import load_model


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--prompt",
        action="append",
        dest="prompts",
        help="Exact prompt text to compare; may be supplied more than once.",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    checkpoint_sha = sha256_file(args.checkpoint)
    if manifest.get("checkpoint", {}).get("sha256") != checkpoint_sha:
        raise SystemExit("STOP: checkpoint SHA-256 does not match the Safari bundle manifest.")

    model, tokenizer, device = load_model(str(args.checkpoint), device="cpu")
    if not hasattr(tokenizer, "to_dict"):
        raise SystemExit("STOP: parity export requires the native byte-BPE tokenizer.")
    if tokenizer.to_dict() != manifest.get("tokenizer"):
        raise SystemExit("STOP: checkpoint tokenizer does not exactly match the Safari manifest.")

    prompts = args.prompts or [
        "المستخدم: مرحبًا، من أنت؟\nJon2:",
        "المستخدم: اشرح الذكاء الاصطناعي بلغة بسيطة.\nJon2:",
        "المستخدم: إذا كان معي 10 جنيهات واشتريت شيئًا بأربعة، فكم يتبقى؟\nJon2:",
        "المستخدم: إزيك؟ ممكن تشرحلي يعني إيه تعلم آلي؟\nJon2:",
    ]

    records = []
    model.eval()
    with torch.inference_mode():
        for prompt in prompts:
            token_ids = tokenizer.encode(prompt)
            if not token_ids:
                raise SystemExit("STOP: a parity prompt encoded to zero tokens.")
            bounded_ids = token_ids[-model.context:]
            input_tensor = torch.tensor([bounded_ids], dtype=torch.long, device=device)
            logits = model(input_tensor)[0, -1, :].detach().cpu().tolist()
            records.append({
                "prompt": prompt,
                "token_ids": token_ids,
                "bounded_token_ids": bounded_ids,
                "python_argmax": max(range(len(logits)), key=logits.__getitem__),
                "python_logits": logits,
            })

    result = {
        "format": "jon2-python-safari-parity-reference-v1",
        "checkpoint_sha256": checkpoint_sha,
        "weights_sha256": manifest.get("weights_sha256"),
        "config": manifest.get("config"),
        "tokenizer_vocab_size": tokenizer.vocab_size,
        "prompts": records,
        "private_artifact_notice": "Contains reference logits; keep private and do not commit.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Reference written: {args.output}")
    print(f"Checkpoint SHA-256: {checkpoint_sha}")
    print(f"Prompts compared: {len(records)}")
    print("This is numerical parity evidence only, not an Arabic quality pass.")


if __name__ == "__main__":
    main()
