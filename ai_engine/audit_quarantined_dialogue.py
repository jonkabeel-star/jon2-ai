"""Read-only audit for quarantined Jon2 Arabic dialogue JSONL proposals.
This tool never approves data, moves files into training_data, or starts training.
"""
from __future__ import annotations
import argparse, hashlib, json, unicodedata
from collections import Counter
from pathlib import Path

def _normalise(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())

def audit_jsonl(path: Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    ids, prompts, duplicate_ids, duplicate_prompts = set(), set(), [], []
    categories, dialects = Counter(), Counter()
    role_errors, records = [], []
    total_messages = total_chars = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip(): continue
        try: item = json.loads(line)
        except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON on line {line_no}: {exc.msg}") from exc
        if not isinstance(item, dict): raise ValueError(f"Line {line_no} must be a JSON object.")
        sample_id = item.get("id")
        if not isinstance(sample_id, str) or not sample_id.strip(): raise ValueError(f"Line {line_no} is missing a non-empty id.")
        if sample_id in ids: duplicate_ids.append(sample_id)
        ids.add(sample_id)
        messages = item.get("messages")
        if not isinstance(messages, list) or len(messages) < 2: raise ValueError(f"Line {line_no} needs at least two messages.")
        expected, user_prompt_seen = "user", False
        for index, message in enumerate(messages):
            if not isinstance(message, dict): raise ValueError(f"Line {line_no}, message {index}: expected an object.")
            role, content = message.get("role"), message.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                raise ValueError(f"Line {line_no}, message {index}: invalid role/content.")
            if role != expected: role_errors.append(f"{sample_id}: expected {expected}, got {role}")
            expected = "assistant" if role == "user" else "user"
            if role == "user" and not user_prompt_seen:
                key = _normalise(content)
                if key in prompts: duplicate_prompts.append(sample_id)
                prompts.add(key); user_prompt_seen = True
            total_chars += len(content)
        if not user_prompt_seen or messages[-1].get("role") != "assistant":
            role_errors.append(f"{sample_id}: conversation must start with user and end with assistant")
        total_messages += len(messages)
        categories[str(item.get("category", "unspecified"))] += 1
        dialects[str(item.get("dialect", "unspecified"))] += 1
        records.append(sample_id)
    if not records: raise ValueError("No JSONL records found.")
    valid = not duplicate_ids and not duplicate_prompts and not role_errors
    return {
        "file": path.name, "status": "QUARANTINED_NOT_APPROVED",
        "training_eligible": False, "approval_required": True,
        "record_count": len(records), "message_count": total_messages,
        "content_character_count": total_chars, "file_character_count": len(text),
        "file_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "dialect_labels": dict(sorted(dialects.items())),
        "category_labels": dict(sorted(categories.items())),
        "duplicate_ids": duplicate_ids, "duplicate_first_user_prompts": duplicate_prompts,
        "role_sequence_errors": role_errors, "structurally_valid": valid,
        "limitations": [
            "Structural validity is not factual, linguistic, privacy, or legal approval.",
            "Dialect labels are author-supplied metadata, not automatic dialect detection.",
            "This report does not grant training permission or modify any training manifest."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_jsonl(args.jsonl)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["structurally_valid"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
