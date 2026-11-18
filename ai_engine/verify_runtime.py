"""Private Jon2 Arabic inference smoke test; never opens the public release gate."""
import json
import sys
from chat_engine import checkpoint_sha256, checkpoint_is_valid, generate_reply, load_runtime, model_is_ready

PROMPTS = [
    ("MSA", "ما عاصمة مصر؟"),
    ("Egyptian", "إزيك؟ عامل إيه النهارده؟"),
    ("Reasoning", "إذا كان مع أحمد 5 تفاحات وأعطى صديقه تفاحتين، فكم تفاحة بقيت معه؟"),
]

def main() -> int:
    if not checkpoint_is_valid():
        print(json.dumps({"status": "blocked", "reason": "checkpoint_missing_or_sha256_mismatch", "sha256": checkpoint_sha256()}, ensure_ascii=False, indent=2))
        return 2
    try:
        load_runtime()
        if not model_is_ready():
            raise RuntimeError("Model/tokenizer did not load.")
    except Exception as exc:
        print(json.dumps({"status": "load_failed", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
        return 3
    results = []
    for category, prompt in PROMPTS:
        try:
            reply = generate_reply(prompt)
            results.append({"category": category, "prompt": prompt, "reply": reply, "surface_check": "passed"})
        except Exception as exc:
            results.append({"category": category, "prompt": prompt, "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps({"status": "inference_executed", "checkpoint_sha256": checkpoint_sha256(), "model_loaded": model_is_ready(), "human_semantic_review_required": True, "release_gate_changed": False, "results": results}, ensure_ascii=False, indent=2))
    return 0 if all("reply" in item for item in results) else 4

if __name__ == "__main__":
    sys.exit(main())
