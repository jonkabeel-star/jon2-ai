"""Local Ollama coding model; generated patches are tested only in isolated Docker."""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

DENIED={"source_approval.py","preflight_training.py","train_jon2.py","autonomous_builder.py","training_gate.py"}
DIFF=re.compile(r"^diff --git a/(.+?) b/(.+?)$",re.MULTILINE)
FENCED_DIFF=re.compile(r"```(?:diff)?\s*\n(.*?)\n```",re.DOTALL|re.IGNORECASE)

def collect_context(repo, limit=40000):
    """Give the local coding model actual, bounded source context; never read data or weights."""
    root=Path(repo)/"ai_engine"
    chunks=[]
    used=0
    if not root.is_dir():
        raise FileNotFoundError("ai_engine directory is missing.")
    for path in sorted(root.glob("*.py")):
        if path.name in DENIED or not path.is_file():
            continue
        try:
            source=path.read_text(encoding="utf-8")
        except (OSError,UnicodeError):
            continue
        block=f"\n--- BEGIN {path.as_posix()} ---\n{source[:12000]}\n--- END {path.as_posix()} ---\n"
        if used+len(block)>limit:
            break
        chunks.append(block)
        used+=len(block)
    return "".join(chunks)

def extract_patch(content):
    """Extract only the unified diff, discarding markdown fences and trailing model chatter."""
    content=(content or "").strip()
    match=FENCED_DIFF.search(content)
    if match:
        content=match.group(1).strip()
    if content=="NO_SAFE_PATCH" or content.startswith("NO_SAFE_PATCH\n"):
        return "NO_SAFE_PATCH"
    start=content.find("diff --git ")
    if start<0:
        return content
    return content[start:].strip()

def propose(task,model,host,repo):
    context=collect_context(repo)
    data=json.dumps({"model":model,"stream":False,"options":{"temperature":0.1},"messages":[
      {"role":"system","content":"You are a careful code repair model. Use only the supplied current source files. Return exactly one valid unified git diff with diff --git headers and correct context, or exactly NO_SAFE_PATCH. Do not use markdown fences or add explanations. Minimal Python-only changes under ai_engine/. Never alter rights gates, training, weights, data, CI, deployment, dependencies, secrets or shell/network behavior."},
      {"role":"user","content":task+"\n\nCURRENT REPOSITORY SOURCE (authoritative; do not invent files or functions):\n"+context}]}).encode()
    req=urllib.request.Request(host.rstrip("/")+"/api/chat",data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=240) as response: body=json.loads(response.read().decode())
    return extract_patch(body.get("message",{}).get("content",""))

def validate(patch):
    pairs=DIFF.findall(patch)
    if not pairs: raise ValueError("No valid unified git diff returned.")
    paths=[]
    for old,new in pairs:
        p=Path(new)
        if (old!=new or p.is_absolute() or ".." in p.parts
                or len(p.parts)<2 or p.parts[0]!="ai_engine"
                or not new.endswith(".py") or p.name in DENIED
                or any(x in {".git","training_data","checkpoints","models","__pycache__",".venv"} for x in p.parts)):
            raise PermissionError("Protected or out-of-scope patch path: "+new)
        paths.append(new)
    return sorted(set(paths))

def sandbox(repo,patch,image):
    docker=shutil.which("docker")
    if not docker: raise RuntimeError("Docker is required; refusing to execute generated code on host.")
    with tempfile.TemporaryDirectory(prefix="jon2-sandbox-") as tmp:
        root=Path(tmp); work=root/"work"; work.mkdir()
        shutil.copytree(repo/"ai_engine",work/"ai_engine",ignore=shutil.ignore_patterns("__pycache__","*.pyc","training_data","checkpoints","models"))
        pf=root/"patch.diff"; pf.write_text(patch,encoding="utf-8")
        check=subprocess.run(["git","apply","--recount","--check",str(pf)],cwd=work,capture_output=True,text=True,timeout=30)
        if check.returncode: raise ValueError("Patch does not apply: "+check.stderr[-1500:])
        apply=subprocess.run(["git","apply","--recount",str(pf)],cwd=work,capture_output=True,text=True,timeout=30)
        if apply.returncode: raise ValueError("Patch application failed: "+apply.stderr[-1500:])
        cmd=[docker,"run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","96","--memory","2g","--cpus","2","--tmpfs","/tmp:rw,noexec,nosuid,size=64m","-e","PYTHONDONTWRITEBYTECODE=1","-v",f"{work}:/work:ro","-w","/work/ai_engine",image,"python","-m","unittest","test_quality_evaluator","test_engineer_agent","test_coding_agent","-v"]
        test=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        return {"tests_passed":test.returncode==0,"test_exit_code":test.returncode,"test_log":(test.stdout+"\n"+test.stderr)[-8000:],"executed_inside_no_network_docker":True,"committed_or_pushed":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",default="."); p.add_argument("--task",required=True)
    p.add_argument("--model",default=os.getenv("JON2_CODER_MODEL","qwen2.5-coder:1.5b"))
    p.add_argument("--host",default=os.getenv("OLLAMA_HOST","http://127.0.0.1:11434"))
    p.add_argument("--docker-image",default="python:3.11-slim")
    p.add_argument("--output",default="artifacts/jon2-proposed.patch")
    p.add_argument("--report",default="artifacts/jon2-coding-agent-report.json")
    a=p.parse_args()
    repo=Path(a.repo).resolve()
    report_path=Path(a.report)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    patch=propose(a.task,a.model,a.host,repo)
    if patch=="NO_SAFE_PATCH":
        result={"model":a.model,"outcome":"no_safe_patch_needed","changed_paths":[],
                "tests_passed":None,"executed_inside_no_network_docker":False,
                "committed_or_pushed":False,"human_review_required":True,
                "passed":True,"note":"The coding model explicitly declined to propose a change."}
        report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    try:
        paths=validate(patch)
        out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(patch+"\n",encoding="utf-8")
        result=sandbox(repo,patch,a.docker_image)
        outcome="patch_tested"
    except (ValueError, PermissionError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        paths=[]
        outcome="rejected_or_not_sandboxed"
        result={"tests_passed":False,"test_exit_code":None,
                "test_log":str(exc),"executed_inside_no_network_docker":False,
                "committed_or_pushed":False,"passed":False}
    result.update({"model":a.model,"outcome":outcome,"changed_paths":paths,
                   "human_review_required":True,"passed":result["tests_passed"]})
    report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["tests_passed"] else 2
if __name__=="__main__": raise SystemExit(main())
