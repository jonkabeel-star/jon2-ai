"""Training is dry-run by default; explicit execute requires all gates."""
from __future__ import annotations
import argparse,json,subprocess,sys
from datetime import datetime
from pathlib import Path
from preflight_training import build_report
from model_profiles import describe_profile

def prepare(data,approvals,profile,checkpoint,minimum_chars=100000,minimum_ratio=10.0):
    report=build_report(data_dir=data,approval_manifest=approvals,profile_name=profile,minimum_characters=minimum_chars,minimum_tokens_per_parameter=minimum_ratio)
    try:
        import torch
        cuda=torch.cuda.is_available()
        gpu=torch.cuda.get_device_name(0) if cuda else None
    except Exception: cuda=False; gpu=None
    target=checkpoint.resolve()
    ready=bool(report["readiness"]["ready"] and cuda and not target.exists())
    return {"profile":profile,"readiness":report["readiness"],"source_approval_passed":True,"cuda_available":cuda,"gpu_name":gpu,"checkpoint_path":str(target),"checkpoint_path_is_new":not target.exists(),"authorized_to_train":ready,"training_started":False,"reason":"All gates passed; explicit --execute required." if ready else "Blocked by rights, data/token sufficiency, GPU, or existing checkpoint."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="ai_engine/training_data"); p.add_argument("--approvals",default="ai_engine/training_data/source_approvals.json")
    p.add_argument("--profile",default="arabic_30m"); p.add_argument("--checkpoint",default="")
    p.add_argument("--minimum-characters",type=int,default=100000); p.add_argument("--minimum-tokens-per-parameter",type=float,default=10.0)
    p.add_argument("--steps",type=int,default=1000); p.add_argument("--execute",action="store_true")
    p.add_argument("--report",default="artifacts/jon2-training-gate.json")
    a=p.parse_args()
    if a.minimum_tokens_per_parameter<10: p.error("Token/parameter guard cannot be lowered below 10.")
    if a.steps<1: p.error("steps must be positive")
    describe_profile(a.profile)
    checkpoint=Path(a.checkpoint) if a.checkpoint else Path("ai_engine/checkpoints/gated-"+a.profile+"-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".pt")
    result=prepare(Path(a.data),Path(a.approvals),a.profile,checkpoint,a.minimum_characters,a.minimum_tokens_per_parameter)
    if a.execute and result["authorized_to_train"]:
        last=checkpoint.with_name(checkpoint.stem+"-last.pt")
        cmd=[sys.executable,"ai_engine/train_jon2.py","--data",a.data,"--approval-manifest",a.approvals,"--profile",a.profile,"--steps",str(a.steps),"--minimum-tokens-per-parameter",str(a.minimum_tokens_per_parameter),"--minimum-chars",str(a.minimum_characters),"--output",str(checkpoint),"--last-checkpoint",str(last),"--keep-last"]
        done=subprocess.run(cmd,check=False); result["training_started"]=done.returncode==0; result["trainer_exit_code"]=done.returncode
    elif a.execute: result["training_blocked"]=True
    out=Path(a.report); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["authorized_to_train"] else 2
if __name__=="__main__": raise SystemExit(main())
