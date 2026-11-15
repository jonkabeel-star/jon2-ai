"""Safe, pull-based Kaggle control bridge for Jon2.

Only allow-listed read-only diagnostics are executable. No shell, eval, training,
checkpoint writes, uploads, deletes, or deployment commands are implemented.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://api.github.com"
POLL_SECONDS = 30
MAX_RUNTIME_SECONDS = 3 * 60 * 60
MAX_TASKS_PER_SESSION = 50
SAFE_ROOTS = (Path("/kaggle/input").resolve(), Path("/kaggle/working").resolve())
TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
ALLOWED_COMMANDS = {
    "audit_environment",
    "list_training_files",
    "checkpoint_metadata",
    "sha256_file",
    "tokenizer_checkpoint_audit",
    "model_quality_audit",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_secrets() -> tuple[str, str, str]:
    try:
        from kaggle_secrets import UserSecretsClient
    except Exception as exc:
        raise RuntimeError("Kaggle Secrets is unavailable. Run this inside Kaggle.") from exc
    client = UserSecretsClient()
    token = client.get_secret("JON2_BRIDGE_TOKEN")
    repo = client.get_secret("JON2_BRIDGE_REPO")
    control_branch = client.get_secret("JON2_BRIDGE_BRANCH")
    if not token or not repo or "/" not in repo or not control_branch:
        raise RuntimeError(
            "Add Kaggle Secrets JON2_BRIDGE_TOKEN, JON2_BRIDGE_REPO "
            "(owner/private-repo), and JON2_BRIDGE_BRANCH. Values are never printed."
        )
    return token.strip(), repo.strip(), control_branch.strip()


class GitHubBridge:
    def __init__(self, token: str, repo: str, branch: str):
        self.repo = repo
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", branch) or ".." in branch.split("/"):
            raise ValueError("Invalid bridge branch name")
        self.branch = branch
        self.session = requests.Session()
        # Retry transient network disconnects on safe read requests.
        retry = Retry(
            total=6,
            connect=6,
            read=6,
            status=4,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        response = self.session.get(f"{API}/repos/{repo}", timeout=20)
        response.raise_for_status()
        metadata = response.json()
        if metadata.get("private") is not True:
            raise RuntimeError("Control repository must be PRIVATE. Bridge stopped.")
        self.default_branch = metadata.get("default_branch") or "main"

    def list_inbox(self) -> list[dict[str, Any]]:
        url = f"{API}/repos/{self.repo}/contents/bridge/inbox"
        response = self.session.get(url, params={"ref": self.branch}, timeout=20)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        items = response.json()
        return [x for x in items if x.get("type") == "file" and x.get("name", "").endswith(".json")]

    def read_json(self, path: str) -> dict[str, Any]:
        response = self.session.get(
            f"{API}/repos/{self.repo}/contents/{path}",
            params={"ref": self.branch},
            timeout=20,
        )
        response.raise_for_status()
        raw = base64.b64decode(response.json()["content"]).decode("utf-8")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("JSON document must be an object")
        return value

    def exists(self, path: str) -> bool:
        response = self.session.get(
            f"{API}/repos/{self.repo}/contents/{path}",
            params={"ref": self.branch},
            timeout=20,
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def write_json_once(self, path: str, value: dict[str, Any]) -> None:
        if self.exists(path):
            existing = self.read_json(path)
            if existing == value:
                return
            raise RuntimeError(f"Refusing to overwrite a different bridge record: {path}")
        body = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        response = self.session.put(
            f"{API}/repos/{self.repo}/contents/{path}",
            json={
                "message": f"Jon2 bridge result: {Path(path).stem}",
                "content": base64.b64encode(body).decode("ascii"),
                "branch": self.branch,
            },
            timeout=20,
        )
        response.raise_for_status()


def safe_path(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("A non-empty path argument is required")
    path = Path(value).resolve()
    if not any(path == root or root in path.parents for root in SAFE_ROOTS):
        raise ValueError("Path is outside /kaggle/input and /kaggle/working")
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def audit_environment(_: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": os.sys.version.split()[0],
        "roots": {},
    }
    try:
        import torch
        report["pytorch"] = torch.__version__
        report["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            report["cuda_device"] = torch.cuda.get_device_name(0)
    except Exception as exc:
        report["pytorch"] = f"unavailable: {type(exc).__name__}"
    for root in SAFE_ROOTS:
        files = [p for p in root.rglob("*") if p.is_file()]
        report["roots"][str(root)] = {
            "file_count": len(files),
            "total_bytes": sum(p.stat().st_size for p in files),
            "sample_paths": [str(p) for p in files[:100]],
        }
    return report


def list_training_files(_: dict[str, Any]) -> dict[str, Any]:
    extensions = {".txt", ".jsonl", ".json"}
    found = []
    for root in SAFE_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                found.append({
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": digest.hexdigest(),
                })
    return {"count": len(found), "files": found[:500]}


def checkpoint_metadata(args: dict[str, Any]) -> dict[str, Any]:
    path = safe_path(args.get("path"))
    if path.suffix.lower() not in {".pt", ".pth"}:
        raise ValueError("Only .pt and .pth checkpoint files are accepted")
    import torch
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint is not a dictionary")
    fields = {}
    for key in (
        "config", "training_plan", "training_steps", "best_validation_loss",
        "evaluations_without_improvement", "corpus_characters", "corpus_sha256",
        "validation_fraction", "model_name", "training_method",
    ):
        value = checkpoint.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            fields[key] = value
        elif isinstance(value, dict):
            fields[key] = {
                str(k): v for k, v in value.items()
                if isinstance(v, (str, int, float, bool)) or v is None
            }
    tokenizer = checkpoint.get("tokenizer")
    if isinstance(tokenizer, dict):
        fields["tokenizer"] = {
            str(k): v for k, v in tokenizer.items()
            if isinstance(v, (str, int, float, bool)) or v is None
        }
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": digest,
        "metadata": fields,
        "note": "Read-only inspection; model tensors and optimizer state were not exported.",
    }


def sha256_file(args: dict[str, Any]) -> dict[str, Any]:
    path = safe_path(args.get("path"))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}



def tokenizer_checkpoint_audit(args: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the historical tokenizer from an approved corpus without training or writes."""
    data_dir = Path(args.get("data_dir", "")).resolve()
    checkpoint_path = safe_path(args.get("checkpoint_path"))
    tokenizer_file = safe_path(args.get("tokenizer_file"))
    if checkpoint_path.suffix.lower() not in {".pt", ".pth"}:
        raise ValueError("checkpoint_path must point to a .pt or .pth file")
    if tokenizer_file.name != "tokenizer.py":
        raise ValueError("tokenizer_file must be the project's tokenizer.py")
    if not data_dir.is_dir() or not any(
        data_dir == root or root in data_dir.parents for root in SAFE_ROOTS
    ):
        raise ValueError("data_dir must be inside /kaggle/input or /kaggle/working")
    txt_files = sorted(data_dir.rglob("*.txt"))
    if not txt_files:
        raise FileNotFoundError("No .txt corpus files found in data_dir")
    parts = []
    for source in txt_files:
        lines = source.read_text(encoding="utf-8", errors="strict").splitlines()
        useful = [line for line in lines if not line.lstrip().startswith("#")]
        cleaned = "\\n".join(useful).strip()
        if cleaned:
            parts.append(cleaned)
    corpus = "\\n\\n".join(parts).strip()
    if len(corpus) < 1000:
        raise ValueError("Reconstructed corpus is unexpectedly short")
    import importlib.util
    import torch
    spec = importlib.util.spec_from_file_location("jon2_audit_tokenizer", tokenizer_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the supplied Jon2 tokenizer module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    corpus_hash = hashlib.sha256(corpus.encode("utf-8")).hexdigest()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("tokenizer"), dict):
        raise ValueError("Checkpoint does not contain a serialized tokenizer")
    plan = checkpoint.get("training_plan") or {}
    split_name = plan.get("validation_split_algorithm")
    if split_name != "seeded_paragraph_blocks_v1":
        raise ValueError(f"Unsupported historical split algorithm: {split_name!r}")
    import math
    import random
    blocks = [b.strip() for b in re.split(r"\\n\\s*\\n", corpus) if b.strip()]
    indices = list(range(len(blocks)))
    seed = int(plan.get("seed", 42))
    fraction = float(plan.get("validation_fraction", checkpoint.get("validation_fraction", 0.1)))
    random.Random(seed).shuffle(indices)
    validation_count = max(1, math.ceil(len(blocks) * fraction))
    validation_indices = set(indices[:validation_count])
    train_text = "\\n\\n".join(b for i, b in enumerate(blocks) if i not in validation_indices)
    expected_corpus_hash = checkpoint.get("corpus_sha256")
    tokenizer_config = checkpoint["tokenizer"]
    vocab_size = int(plan.get("tokenizer_vocab_size", 512))
    min_frequency = int(plan.get("tokenizer_min_frequency", 2))
    rebuilt = module.ByteBPETokenizer.train(
        train_text, vocab_size=vocab_size, min_frequency=min_frequency
    )
    rebuilt_dict = rebuilt.to_dict()
    return {
        "corpus_characters": len(corpus),
        "corpus_sha256": corpus_hash,
        "checkpoint_corpus_sha256": expected_corpus_hash,
        "corpus_matches_checkpoint": corpus_hash == expected_corpus_hash,
        "paragraph_blocks": len(blocks),
        "training_blocks": len(blocks) - validation_count,
        "validation_blocks": validation_count,
        "training_characters": len(train_text),
        "validation_fraction": fraction,
        "seed": seed,
        "tokenizer_matches_checkpoint": rebuilt_dict == tokenizer_config,
        "rebuilt_vocab_size": getattr(rebuilt, "vocab_size", None),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "note": "Read-only audit. No training, checkpoint writes, or model-weight changes.",
    }



def model_quality_audit(args: dict[str, Any]) -> dict[str, Any]:
    """Run fixed deterministic inference prompts; never train or write model files."""
    checkpoint_path = safe_path(args.get("checkpoint_path"))
    core_file = safe_path(args.get("core_file"))
    if checkpoint_path.suffix.lower() not in {".pt", ".pth"}:
        raise ValueError("checkpoint_path must point to a .pt or .pth file")
    if core_file.name != "jon2_core.py":
        raise ValueError("core_file must be the project's jon2_core.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("jon2_quality_core", core_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the supplied Jon2 core module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    load_model = getattr(module, "load_model", None)
    generate = getattr(module, "generate", None)
    if not callable(load_model) or not callable(generate):
        raise RuntimeError("Jon2 core must expose load_model and generate")
    model, tokenizer, device = load_model(str(checkpoint_path), device="cpu")
    prompts = [
        "المستخدم: ما عاصمة مصر؟\nJon2: ",
        "المستخدم: إزيك يا صاحبي؟ عامل إيه؟\nJon2: ",
        "المستخدم: اشرح معنى الصداقة باختصار.\nJon2: ",
        "المستخدم: كم يساوي اثنان زائد ثلاثة؟\nJon2: ",
        "المستخدم: لماذا نتعلم اللغة العربية؟\nJon2: ",
    ]
    outputs = []
    for prompt in prompts:
        answer = generate(
            model, tokenizer, prompt, device,
            max_new_chars=220,
            temperature=0.8,
            do_sample=False,
            repetition_penalty=1.12,
            no_repeat_ngram_size=3,
            top_k=40,
        )
        outputs.append({"prompt": prompt, "output": str(answer)})
    return {
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "device": str(device),
        "tokenizer_vocab_size": getattr(tokenizer, "vocab_size", None),
        "samples": outputs,
        "note": "Deterministic inference-only quality snapshot. No optimizer, training, or checkpoint writes.",
    }


HANDLERS = {
    "audit_environment": audit_environment,
    "list_training_files": list_training_files,
    "checkpoint_metadata": checkpoint_metadata,
    "sha256_file": sha256_file,
    "tokenizer_checkpoint_audit": tokenizer_checkpoint_audit,
    "model_quality_audit": model_quality_audit,
}


def process_task(bridge: GitHubBridge, item: dict[str, Any]) -> bool:
    task_path = item["path"]
    filename = item["name"]
    task_id = filename[:-5]
    if not TASK_ID_RE.fullmatch(task_id):
        print(f"Skipping invalid task filename: {filename}")
        return False
    receipt_path = f"bridge/receipts/{task_id}.json"
    result_path = f"bridge/outbox/{task_id}.json"
    if bridge.exists(receipt_path):
        return False

    # Recover cleanly if the result was written but the receipt write failed.
    if bridge.exists(result_path):
        existing_result = bridge.read_json(result_path)
        if existing_result.get("task_id") != task_id:
            raise RuntimeError(f"Existing result belongs to another task: {result_path}")
        bridge.write_json_once(receipt_path, {
            "task_id": task_id,
            "status": existing_result.get("status", "unknown"),
            "completed_at": existing_result.get("completed_at", utc_now()),
            "result_path": result_path,
        })
        print(f"Task {task_id}: receipt recovered")
        return True

    started = utc_now()
    result: dict[str, Any] = {
        "task_id": task_id,
        "started_at": started,
        "completed_at": utc_now(),
        "status": "error",
    }
    try:
        task = bridge.read_json(task_path)
        if task.get("id") != task_id:
            raise ValueError("Task id does not match its filename")
        command = task.get("command")
        args = task.get("args", {})
        if command not in ALLOWED_COMMANDS:
            raise ValueError(f"Command is not allow-listed: {command!r}")
        if not isinstance(args, dict):
            raise ValueError("Task args must be a JSON object")
        payload = HANDLERS[command](args)
        result.update({
            "completed_at": utc_now(),
            "status": "success",
            "command": command,
            "result": payload,
        })
    except Exception as exc:
        result.update({
            "completed_at": utc_now(),
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        })

    bridge.write_json_once(result_path, result)
    bridge.write_json_once(receipt_path, {
        "task_id": task_id,
        "status": result["status"],
        "completed_at": result["completed_at"],
        "result_path": f"bridge/outbox/{task_id}.json",
    })
    print(f"Task {task_id}: {result['status']}")
    return True


def main() -> None:
    token, repo, branch = get_secrets()
    bridge = GitHubBridge(token, repo, branch)
    print("Jon2 Kaggle Bridge connected to a verified private repository.")
    print(f"Control branch: {branch}")
    print("Allow-listed commands (read-only audits):", ", ".join(sorted(ALLOWED_COMMANDS)))
    print("No shell execution, training, checkpoint writes, deletes, or deployment.")
    started = time.monotonic()
    processed = 0
    while time.monotonic() - started < MAX_RUNTIME_SECONDS and processed < MAX_TASKS_PER_SESSION:
        try:
            for item in bridge.list_inbox():
                if processed >= MAX_TASKS_PER_SESSION:
                    break
                if process_task(bridge, item):
                    processed += 1
        except requests.RequestException as exc:
            # A temporary Kaggle/GitHub network drop must not kill the bridge.
            print(f"Temporary GitHub connection error: {type(exc).__name__}. Retrying after delay.")
            time.sleep(min(POLL_SECONDS * 2, 60))
            continue
        time.sleep(POLL_SECONDS)
    print(f"Bridge stopped. Processed tasks this session: {processed}")


if __name__ == "__main__":
    main()
