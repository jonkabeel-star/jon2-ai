"""Evaluate a stronger local Ollama candidate without replacing production Jon2."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from quality_evaluator import evaluate_dataset, load_jsonl
from semantic_evaluator import judge_answer


SYSTEM_PROMPT = (
    "أنت مساعد عربي دقيق. أجب عن السؤال مباشرة وبالعربية فقط. "
    "استخدم اللهجة المصرية إذا كان السؤال بالمصرية والفصحى إذا كان بالفصحى. "
    "لا تخترع معلومات. في الحساب نفّذ العملية وتحقق من الناتج. "
    "إذا لم تعرف فقل إنك لا تعرف. تجنب التكرار والحشو."
)


def ollama_chat(prompt: str, model: str, host: str, timeout: int = 300) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0, "num_predict": 400},
    }
    request = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    answer = body.get("message", {}).get("content")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Candidate Ollama model returned an empty answer.")
    return answer.strip()


def run(cases_path: str, answers_path: str, report_path: str, model: str, judge_model: str):
    cases = load_jsonl(Path(cases_path))
    if not cases:
        raise ValueError("Candidate benchmark cases are empty; refusing a vacuous pass.")

    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    answers: dict[str, str] = {}
    for index, case in enumerate(cases, 1):
        test_id = str(case["test_id"])
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Missing benchmark prompt: " + test_id)
        print(f"[candidate {index}/{len(cases)}] {test_id}", flush=True)
        answers[test_id] = ollama_chat(prompt, model, host)

    answer_path = Path(answers_path)
    answer_path.parent.mkdir(parents=True, exist_ok=True)
    answer_path.write_text(
        "".join(
            json.dumps({"test_id": case["test_id"], "answer": answers[str(case["test_id"])]}, ensure_ascii=False) + "\n"
            for case in cases
        ),
        encoding="utf-8",
    )

    lexical = evaluate_dataset(cases, answers)
    judged = {
        str(case["test_id"]): judge_answer(
            case, answers[str(case["test_id"])], model=judge_model, host=host
        )
        for case in cases
    }
    semantic_passed = len(judged) == len(cases) and all(item["passed"] for item in judged.values())
    report = {
        "candidate_model": model,
        "production_model_changed": False,
        "benchmark_cases": len(cases),
        "successful_generations": len(answers),
        "lexical_screening": lexical,
        "semantic_judge_model": judge_model,
        "semantic_judge_results": judged,
        "semantic_passed": semantic_passed,
        "release_or_training_approval": False,
        "human_review_required": True,
    }
    report_path_obj = Path(report_path)
    report_path_obj.parent.mkdir(parents=True, exist_ok=True)
    report_path_obj.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="ai_engine/evaluation_cases.jsonl")
    parser.add_argument("--answers", default="artifacts/jon2-candidate-1.5b-answers.jsonl")
    parser.add_argument("--report", default="artifacts/jon2-candidate-1.5b-evaluation.json")
    parser.add_argument("--model", default="qwen2.5:1.5b")
    parser.add_argument("--judge-model", default="qwen2.5:3b")
    args = parser.parse_args()
    result = run(args.cases, args.answers, args.report, args.model, args.judge_model)
    return 0 if result["semantic_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
