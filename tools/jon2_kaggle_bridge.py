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
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_secrets() -> tuple[str, str]:
    try:
        from kaggle_secrets import UserSecretsClient
    except Exception as exc:
        raise RuntimeError("Kaggle Secrets is unavailable. Run this inside Kaggle.") from exc
    client = UserSecretsClient()
    token = client.get_secret("JON2_BRIDGE_TOKEN")
    repo = client.get_secret("JON2_BRIDGE_REPO")
    control_branch = client.get_secret("JON2_BRIDGE_BRANCH")
    if not token or not repo or "/" not in repo:
        raise RuntimeError(
            "Add Kaggle Secrets JON2_BRIDGE_TOKEN and JON2_BRIDGE_REPO "
            "(owner/private-repo). Values are never printed."
        )
    return token.strip(), repo.strip(), (control_branch.strip() if control_branch else "main")


class GitHubBridge:
    def __init__(self, token: str, repo: str, branch: str):
        self.repo = repo
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", branch) or ".." in branch.split("/"):
            raise ValueError("Invalid bridge branch name")
        self.branch = branch
        self.session = requests.Session()
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
            params={"ref": self.default_branch},
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
            params={"ref": self.default_branch},
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


HANDLERS = {
    "audit_environment": audit_environment,
    "list_training_files": list_training_files,
    "checkpoint_metadata": checkpoint_metadata,
    "sha256_file": sha256_file,
}


def process_task(bridge: GitHubBridge, item: dict[str, Any]) -> bool:
    task_path = item["path"]
    filename = item["name"]
    task_id = filename[:-5]
    if not TASK_ID_RE.fullmatch(task_id):
        print(f"Skipping invalid task filename: {filename}")
        return False
    receipt_path = f"bridge/receipts/{task_id}.json"
    if bridge.exists(receipt_path):
        return False

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

    bridge.write_json_once(f"bridge/outbox/{task_id}.json", result)
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
    print("Allow-listed read-only commands:", ", ".join(sorted(ALLOWED_COMMANDS)))
    print("No shell execution, training, checkpoint writes, deletes, or deployment.")
    started = time.monotonic()
    processed = 0
    while time.monotonic() - started < MAX_RUNTIME_SECONDS and processed < MAX_TASKS_PER_SESSION:
        for item in bridge.list_inbox():
            if processed >= MAX_TASKS_PER_SESSION:
                break
            if process_task(bridge, item):
                processed += 1
        time.sleep(POLL_SECONDS)
    print(f"Bridge stopped. Processed tasks this session: {processed}")


if __name__ == "__main__":
    main()
