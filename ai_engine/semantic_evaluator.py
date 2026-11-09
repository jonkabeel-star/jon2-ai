"""Local Ollama semantic judge. Fallible second opinion; fail closed."""
from __future__ import annotations
import json, os, urllib.request
from typing import Any

def _chat(messages, model=None, host=None, timeout=180):
    base=(host or os.getenv("OLLAMA_HOST","http://127.0.0.1:11434")).rstrip("/")
    selected=model or os.getenv("JON2_JUDGE_MODEL","qwen2.5:3b")
    data=json.dumps({"model":selected,"messages":messages,"stream":False,"format":"json","options":{"temperature":0}}).encode()
    req=urllib.request.Request(base+"/api/chat",data=data,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            body=json.loads(response.read().decode())
    except Exception as exc:
        raise RuntimeError("Local Ollama judge unavailable: "+str(exc)) from exc
    content=body.get("message",{}).get("content")
    if not isinstance(content,str) or not content.strip():
        raise RuntimeError("Semantic judge returned no content.")
    return content

def judge_answer(case: dict[str,Any], answer: str, *, model=None, host=None):
    reference=case.get("reference_answer")
    if not isinstance(reference,str) or not reference.strip():
        raise ValueError("A reviewed reference_answer is required.")
    payload={"test_id":case.get("test_id"),"dialect":case.get("dialect"),"question":case.get("prompt"),"reference_answer":reference,"required_concepts":case.get("expected_terms",[]),"forbidden_claims":case.get("forbidden_terms",[]),"candidate_answer":answer}
    system=("Strict Arabic evaluator. Compare meaning, factual correctness, relevance, unsupported claims, and dialect suitability; accept valid paraphrases. Do not reward keyword copying. If uncertain, fail. Return JSON keys: semantically_correct, answers_question, contains_material_error, contains_unsupported_claim, dialect_appropriate (booleans), confidence (0..1), rationale (Arabic string), issues (string array).")
    raw=_chat([{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}],model,host)
    try: result=json.loads(raw)
    except json.JSONDecodeError as exc: raise RuntimeError("Judge did not return valid JSON.") from exc
    keys=("semantically_correct","answers_question","contains_material_error","contains_unsupported_claim","dialect_appropriate")
    if any(type(result.get(k)) is not bool for k in keys): raise RuntimeError("Judge response missing boolean fields.")
    confidence=result.get("confidence")
    if not isinstance(confidence,(int,float)) or isinstance(confidence,bool) or not 0<=confidence<=1: raise RuntimeError("Invalid judge confidence.")
    issues=result.get("issues",[])
    if not isinstance(issues,list) or not all(isinstance(x,str) for x in issues): raise RuntimeError("Invalid judge issues.")
    passed=all(result[k] for k in ("semantically_correct","answers_question","dialect_appropriate")) and not result["contains_material_error"] and not result["contains_unsupported_claim"] and confidence>=0.75
    return {"judge_model":model or os.getenv("JON2_JUDGE_MODEL","qwen2.5:3b"),"passed":passed,**{k:result[k] for k in keys},"confidence":float(confidence),"rationale":str(result.get("rationale",""))[:1200],"issues":issues[:20],"human_review_required":True}
