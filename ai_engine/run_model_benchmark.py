"""Generate and evaluate answers from the real Jon2 model."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from language_engine import Jon2LanguageEngine
from quality_evaluator import evaluate_dataset, load_jsonl
from semantic_evaluator import judge_answer

def run(cases_path, answers_path, report_path, semantic=False, judge_model=None):
    cases=load_jsonl(Path(cases_path))
    engine=Jon2LanguageEngine()
    if not engine.load_model(): raise RuntimeError("Real Jon2 model failed to load.")
    answers={}
    for i,case in enumerate(cases,1):
        key=str(case["test_id"]); prompt=case.get("prompt")
        if not isinstance(prompt,str) or not prompt.strip(): raise ValueError("Missing prompt: "+key)
        print(f"[{i}/{len(cases)}] {key}",flush=True)
        answers[key]=engine.generate(prompt,max_words=400)
    ap=Path(answers_path); ap.parent.mkdir(parents=True,exist_ok=True)
    ap.write_text("".join(json.dumps({"test_id":c["test_id"],"answer":answers[str(c["test_id"])]},ensure_ascii=False)+"\n" for c in cases),encoding="utf-8")
    lexical=evaluate_dataset(cases,answers)
    judged={}
    if semantic:
        for case in cases: judged[str(case["test_id"])]=judge_answer(case,answers[str(case["test_id"])],model=judge_model)
    passed=bool(semantic) and all(x["passed"] for x in judged.values())
    report={"model_name":engine.model_name,"benchmark_cases":len(cases),"real_model_answers_generated":True,"lexical_screening":lexical,"semantic_judging_enabled":semantic,"semantic_judge_results":judged,"semantic_passed":passed,"release_or_training_approval":False,"human_review_required":True}
    rendered=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    rp=Path(report_path); rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(rendered,encoding="utf-8")
    print(rendered); return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",default="ai_engine/evaluation_cases.jsonl")
    p.add_argument("--answers",default="artifacts/jon2-model-answers.jsonl")
    p.add_argument("--report",default="artifacts/jon2-model-evaluation.json")
    p.add_argument("--semantic",action="store_true")
    p.add_argument("--judge-model",default=None)
    a=p.parse_args()
    result=run(a.cases,a.answers,a.report,a.semantic,a.judge_model)
    return 0 if result["semantic_passed"] else 2
if __name__=="__main__": raise SystemExit(main())
