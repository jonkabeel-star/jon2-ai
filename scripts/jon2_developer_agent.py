#!/usr/bin/env python3
"""Bounded Jon2 coding agent: propose small source edits through Cloudflare Workers AI."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

MODEL = "@cf/qwen/qwen3.8-27b"
MAX_CONTEXT_CHARS = 48_000
MAX_FILE_CHARS = 16_000
MAX_TOTAL_OUTPUT = 28_000
MAX_FILES = 2
ALLOWED_ROOTS = {"ai_engine", "server", "tests"}
FORBIDDEN_PARTS = {
    "training_data", "checkpoints", "evaluation", "models", "secrets",
    "weights", "__pycache__", "node_modules", ".git",
}
ALLOWED_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts"}
SYSTEM_PROMPT = """You are Jon2 Developer Agent, a cautious senior software engineer working on the Jon2 AI repository.
Inspect the supplied repository context and choose at most ONE small, high-value, self-contained engineering improvement.
Return ONLY valid JSON with this exact shape:
{"summary":"short explanation in English","files":[{"path":"existing/repository/file.py","content":"complete replacement file content"}]}
Rules:
- Replace at most two EXISTING source files. Do not create, delete, rename, or move files.
- Only edit source files under ai_engine/, server/, or tests/. The caller enforces this.
- Do not edit authentication, authorization, cryptography, billing, secrets, deployment, CI workflows, CORS, model weights, datasets, checkpoints, evaluation prompts, or licensing/approval files.
- Do not add external dependencies or network calls.
- Preserve existing behavior and public interfaces unless a small bug fix requires otherwise.
- Add or improve focused tests when appropriate, but only within tests/.
- Do not claim tests were run. Do not include markdown fences or text outside JSON.
- If no clearly safe, testable improvement is justified by the context, return {"summary":"No safe change identified; more repository context or a human decision is needed.","files":[]}.
- File content must be complete, not a diff or partial snippet.
"""

def fail(message: str) -> None:
    print("Jon2 Developer Agent: " + message, file=sys.stderr)
    raise SystemExit(1)

def tracked_context(root: Path) -> tuple[list[dict], str]:
    listing = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.splitlines()
    chosen: list[dict] = []
    total = 0
    for name in listing:
        path = PurePosixPath(name)
        if not path.parts or path.parts[0] not in ALLOWED_ROOTS:
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            continue
        if name in {"ai_engine/jon2_auto_repair.py", "scripts/jon2_developer_agent.py"}:
            continue
        full = root / name
        if not full.is_file() or full.is_symlink():
            continue
        try:
            content = full.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n[FILE TRUNCATED FOR REVIEW]\n"
        if total + len(content) > MAX_CONTEXT_CHARS:
            break
        chosen.append({"path": name, "content": content})
        total += len(content)
        if len(chosen) >= 18:
            break
    if not chosen:
        fail("No eligible tracked source files were found.")
    return chosen, json.dumps(chosen, ensure_ascii=False)

def call_workers_ai(account_id: str, token: str, context: str) -> str:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{MODEL}"
    body = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Repository source context follows. Select one safe improvement.\n\n" + context},
        ],
        "max_tokens": 7000,
        "temperature": 0.2,
        "top_p": 0.9,
    }
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never print response bodies: they may contain provider or request details.
        fail(f"Workers AI request failed with HTTP {exc.code}. Check the account ID, token scope, model availability, and daily quota.")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        fail("Workers AI could not be reached or returned invalid JSON.")
    if payload.get("success") is not True:
        fail("Workers AI rejected the request. Check the token, model availability, and daily quota.")
    result = payload.get("result") or {}
    answer = result.get("response")
    if not isinstance(answer, str):
        choices = result.get("choices") or []
        if choices and isinstance(choices[0], dict):
            answer = (choices[0].get("message") or {}).get("content")
    if not isinstance(answer, str) or not answer.strip():
        fail("Workers AI returned no text proposal.")
    return answer.strip()

def parse_proposal(answer: str) -> dict:
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", answer, flags=re.I)
    try:
        proposal = json.loads(cleaned)
    except json.JSONDecodeError:
        fail("The model response was not valid JSON; no files were changed.")
    if not isinstance(proposal, dict) or not isinstance(proposal.get("files"), list):
        fail("The model response did not match the required proposal format.")
    if len(proposal["files"]) > MAX_FILES:
        fail("The model proposed too many files; no files were changed.")
    return proposal

def validate_and_apply(root: Path, proposal: dict) -> list[str]:
    files = proposal["files"]
    if not files:
        return []
    validated: list[tuple[Path, str]] = []
    total = 0
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            fail("A proposed file entry was invalid.")
        name, content = item.get("path"), item.get("content")
        if not isinstance(name, str) or not isinstance(content, str):
            fail("A proposed file path or content was invalid.")
        rel = PurePosixPath(name)
        if (rel.is_absolute() or ".." in rel.parts or not rel.parts
            or rel.parts[0] not in ALLOWED_ROOTS
            or rel.suffix.lower() not in ALLOWED_SUFFIXES
            or any(part in FORBIDDEN_PARTS for part in rel.parts)
            or name in seen):
            fail(f"Blocked unsafe path: {name}")
        seen.add(name)
        target = root.joinpath(*rel.parts)
        if target.is_symlink() or not target.is_file():
            fail(f"Only existing regular source files can be edited: {name}")
        if len(content) > MAX_FILE_CHARS:
            fail(f"Proposed file is too large: {name}")
        total += len(content)
        if total > MAX_TOTAL_OUTPUT:
            fail("The total proposed change is too large.")
        validated.append((target, content))
    changed: list[str] = []
    for target, content in validated:
        old = target.read_text(encoding="utf-8")
        if old != content:
            target.write_text(content, encoding="utf-8", newline="")
            changed.append(target.relative_to(root).as_posix())
    return changed

def main() -> int:
    root = Path.cwd().resolve()
    account_id = os.environ.get("JON2_CF_ACCOUNT_ID", "").strip()
    token = os.environ.get("JON2_CF_API_TOKEN", "").strip()
    if not account_id or not token:
        fail("Missing JON2_CF_ACCOUNT_ID or JON2_CF_API_TOKEN GitHub Actions secrets.")
    context_files, context = tracked_context(root)
    answer = call_workers_ai(account_id, token, context)
    proposal = parse_proposal(answer)
    changed = validate_and_apply(root, proposal)
    report = {
        "agent": "Jon2 Developer Agent",
        "version": 1,
        "model": MODEL,
        "summary": str(proposal.get("summary", ""))[:1000],
        "context_files": [item["path"] for item in context_files],
        "changed_files": changed,
        "status": "proposal_created" if changed else "no_change",
        "automatic_merge": False,
        "automatic_deploy": False,
        "human_review_required": True,
    }
    output = root / "jon2-developer-agent-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"changed={'true' if changed else 'false'}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
