from __future__ import annotations
import json
import pytest
from audit_quarantined_dialogue import audit_jsonl

def _write(path, records):
    path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n", encoding="utf-8")

def test_audit_reports_hash_and_keeps_file_quarantined(tmp_path):
    source = tmp_path / "candidate.jsonl"
    _write(source, [{"id":"eg_1","dialect":"egyptian","category":"explanation","messages":[{"role":"user","content":"اشرحلي الفكرة"},{"role":"assistant","content":"هشرحها ببساطة."}]}])
    report = audit_jsonl(source)
    assert report["record_count"] == 1
    assert len(report["sha256"]) == 64
    assert report["structurally_valid"] is True
    assert report["training_eligible"] is False
    assert report["status"] == "QUARANTINED_NOT_APPROVED"

def test_audit_flags_duplicate_ids_and_prompts(tmp_path):
    source = tmp_path / "candidate.jsonl"
    item = {"id":"same","dialect":"msa","category":"reasoning","messages":[{"role":"user","content":"ما الفرق؟"},{"role":"assistant","content":"هذا شرح."}]}
    _write(source, [item, item])
    report = audit_jsonl(source)
    assert report["duplicate_ids"] == ["same"]
    assert report["duplicate_first_user_prompts"] == ["same"]
    assert report["structurally_valid"] is False

def test_audit_rejects_invalid_jsonl(tmp_path):
    source = tmp_path / "broken.jsonl"
    source.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        audit_jsonl(source)

def test_audit_rejects_bad_role_sequence(tmp_path):
    source = tmp_path / "bad_roles.jsonl"
    _write(source, [{"id":"bad","messages":[{"role":"user","content":"سؤال"},{"role":"user","content":"سؤال آخر"}]}])
    report = audit_jsonl(source)
    assert report["structurally_valid"] is False
    assert report["role_sequence_errors"]
