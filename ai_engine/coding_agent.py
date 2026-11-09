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
STANDARD_DIFF=re.compile(r"^--- a/(.+?)\r?\n\+\+\+ b/(.+?)$",re.MULTILINE)
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
    git_start=content.find("diff --git ")
    standard_start=content.find("--- a/")
    starts=[x for x in (git_start,standard_start) if x>=0]
    if not starts:
        return content
    return content[min(starts):].strip()

def _request_ollama_patch(task,model,host,context,previous_invalid=""):
    system=("You are a careful code repair model. Use only the supplied current source files. "
            "Return exactly one valid unified git diff with diff --git headers, ---/+++ paths, "
            "and correct @@ hunk context, or exactly NO_SAFE_PATCH. No markdown fences, JSON, "
            "or explanations. Minimal Python-only changes under ai_engine/. Never alter rights "
            "gates, training, weights, data, CI, deployment, dependencies, secrets, or shell/network behavior.")
    user=task+"\n\nCURRENT REPOSITORY SOURCE (authoritative; do not invent files or functions):\n"+context
    if previous_invalid:
        user += ("\n\nYour previous response was rejected because it was not a valid unified git diff. "
                 "Try once more with correct paths and hunk syntax. If no safe minimal fix is justified, "
                 "return exactly NO_SAFE_PATCH. Previous rejected response (do not copy blindly):\n"
                 + previous_invalid[:6000])
    data=json.dumps({"model":model,"stream":False,"options":{"temperature":0.0},"messages":[
      {"role":"system","content":system},{"role":"user","content":user}]}).encode()
    req=urllib.request.Request(host.rstrip("/")+"/api/chat",data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=240) as response: body=json.loads(response.read().decode())
    return extract_patch(body.get("message",{}).get("content",""))


def check_patch_applicability(repo,patch):
    """Check a proposed diff against the current checkout without changing files."""
    result=subprocess.run(
        ["git","apply","--recount","--check","-"],
        cwd=repo,input=patch,capture_output=True,text=True,timeout=30
    )
    if result.returncode:
        detail=(result.stderr or result.stdout or "git apply --check rejected the patch.")[-2000:]
        raise ValueError("Patch does not apply cleanly to current source: "+detail)
    return True


def propose(task,model,host,repo,max_attempts=2):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("max_attempts must be between 1 and 3.")
    context=collect_context(repo)
    previous_invalid=""
    for attempt in range(1,max_attempts+1):
        patch=_request_ollama_patch(task,model,host,context,previous_invalid)
        if patch=="NO_SAFE_PATCH":
            return patch
        try:
            validate(patch)
            check_patch_applicability(repo,patch)
            return patch
        except (ValueError,PermissionError) as exc:
            previous_invalid=patch
            print(f"Coding model response {attempt}/{max_attempts} rejected: {exc}",flush=True)
            if attempt==max_attempts:
                return patch
    return previous_invalid

def validate(patch):
    pairs=DIFF.findall(patch)
    if not pairs:
        # Some coding models emit standard unified diffs without git headers.
        pairs=STANDARD_DIFF.findall(patch)
    if not pairs: raise ValueError("No valid unified diff returned.")
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
        cmd=[docker,"run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","96","--memory","2g","--cpus","2","--tmpfs","/tmp:rw,noexec,nosuid,size=64m","-e","PYTHONDONTWRITEBYTECODE=1","-v",f"{work}:/work:ro","-w","/work/ai_engine",image,"sh","-lc","python -c \"import ast,pathlib; files=list(pathlib.Path('.').rglob('*.py')); [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in files]; print('Syntax OK:', len(files), 'files')\" && python -m unittest discover -s . -p "test_*.py" -v"]
        test=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        return {"tests_passed":test.returncode==0,"test_exit_code":test.returncode,"test_log":(test.stdout+"\n"+test.stderr)[-8000:],"executed_inside_no_network_docker":True,"committed_or_pushed":False}

def repair_until_green(task,model,host,repo,image,max_rounds=2):
    """Bounded self-repair: each candidate is validated and tested in a fresh sandbox."""
    if type(max_rounds) is not int or not 1 <= max_rounds <= 3:
        raise ValueError("max_rounds must be between 1 and 3.")
    history=[]
    current_task=task
    for round_number in range(1,max_rounds+1):
        patch=propose(current_task,model,host,repo)
        if patch=="NO_SAFE_PATCH":
            if not history:
                return {"outcome":"no_safe_patch_needed","changed_paths":[],"tests_passed":None,
                        "executed_inside_no_network_docker":False,"committed_or_pushed":False,
                        "passed":True,"history":[]}
            return {"outcome":"repair_declined_after_failure","changed_paths":[],"tests_passed":False,
                    "executed_inside_no_network_docker":False,"committed_or_pushed":False,
                    "passed":False,"history":history,"test_log":"Model declined a further repair after a failed candidate."}
        try:
            paths=validate(patch)
            check_patch_applicability(repo,patch)
            result=sandbox(repo,patch,image)
        except (ValueError,PermissionError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
            result={"tests_passed":False,"test_exit_code":None,"test_log":str(exc),
                    "executed_inside_no_network_docker":False,"committed_or_pushed":False}
            paths=[]
        history.append({"round":round_number,"changed_paths":paths,
                        "tests_passed":result["tests_passed"],"test_exit_code":result.get("test_exit_code"),
                        "test_log":result.get("test_log","")[-8000:]})
        if result["tests_passed"]:
            result.update({"outcome":"patch_tested","changed_paths":paths,"passed":True,
                           "history":history,"patch":patch})
            return result
        current_task=(task+"\n\nAUTOMATIC REPAIR FEEDBACK: The previous candidate failed the isolated full Python test suite. "
                      "Do not repeat the same change. Diagnose the failure and propose one minimal corrective diff, "
                      "or return NO_SAFE_PATCH if no safe correction is justified.\n"
                      "FAILED TEST LOG:\n"+result.get("test_log","")[-6000:])
    last=history[-1]
    return {"outcome":"repair_attempts_exhausted","changed_paths":last["changed_paths"],
            "tests_passed":False,"test_exit_code":last["test_exit_code"],
            "test_log":last["test_log"],"executed_inside_no_network_docker":True,
            "committed_or_pushed":False,"passed":False,"history":history}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",default=".")
    parser.add_argument("--task",required=True)
    parser.add_argument("--model",default=os.getenv("JON2_CODER_MODEL","qwen2.5-coder:1.5b"))
    parser.add_argument("--host",default=os.getenv("OLLAMA_HOST","http://127.0.0.1:11434"))
    parser.add_argument("--docker-image",default="python:3.11-slim")
    parser.add_argument("--output",default="artifacts/jon2-proposed.patch")
    parser.add_argument("--report",default="artifacts/jon2-coding-agent-report.json")
    parser.add_argument("--max-repair-rounds",type=int,default=2)
    args=parser.parse_args()
    repo=Path(args.repo).resolve()
    report_path=Path(args.report)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        result=repair_until_green(args.task,args.model,args.host,repo,args.docker_image,args.max_repair_rounds)
        patch=result.pop("patch",None)
        if patch and result.get("tests_passed") is True:
            output=Path(args.output)
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(patch+"\n",encoding="utf-8")
        result.update({"model":args.model,"human_review_required":True})
    except (ValueError,PermissionError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        result={"model":args.model,"outcome":"rejected_or_not_sandboxed","changed_paths":[],
                "tests_passed":False,"test_log":str(exc),"executed_inside_no_network_docker":False,
                "committed_or_pushed":False,"human_review_required":True,"passed":False}
    report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result.get("passed") is True else 2


if __name__=="__main__":
    raise SystemExit(main())
