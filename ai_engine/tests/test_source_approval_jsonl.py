"""Tests for explicit approval of structured Arabic dialogue sources."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from source_approval import validate_source_approvals


class JsonlSourceApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.manifest = self.root / "source_approvals.json"
        (self.data / "base.txt").write_text(
            "نص عربي أصلي للتدريب.\n" * 100, encoding="utf-8"
        )
        self.dialogue = self.data / "dialogue.jsonl"
        self.dialogue.write_text(
            json.dumps({"messages": [
                {"role": "user", "content": "ما عاصمة مصر؟"},
                {"role": "assistant", "content": "عاصمة مصر هي القاهرة."},
            ]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._write_manifest(include_jsonl=False)

    def tearDown(self):
        self.temp.cleanup()

    def _record(self, path):
        raw = path.read_bytes()
        return {
            "file": path.relative_to(self.data).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "character_count": len(raw.decode("utf-8")),
            "status": "APPROVED",
            "reviewer": "Test reviewer",
            "review_date": "2026-11-09",
            "rights_basis": "Test-owned fixture created for automated tests.",
            "intended_use": "research_training",
        }

    def _write_manifest(self, include_jsonl):
        files = [self.data / "base.txt"]
        if include_jsonl:
            files.append(self.dialogue)
        self.manifest.write_text(json.dumps({
            "approved_sources": [self._record(path) for path in files]
        }, ensure_ascii=False), encoding="utf-8")

    def test_default_mode_does_not_include_jsonl(self):
        validate_source_approvals(self.data, self.manifest)

    def test_jsonl_requires_explicit_exact_file_approval(self):
        with self.assertRaises(PermissionError):
            validate_source_approvals(self.data, self.manifest, include_jsonl=True)

    def test_approved_jsonl_passes_exact_hash_and_count_checks(self):
        self._write_manifest(include_jsonl=True)
        validate_source_approvals(self.data, self.manifest, include_jsonl=True)

    def test_jsonl_requires_both_user_and_assistant_turns(self):
        self.dialogue.write_text(json.dumps({"messages": [
            {"role": "user", "content": "سؤال فقط"}
        ]}, ensure_ascii=False) + "\n", encoding="utf-8")
        self._write_manifest(include_jsonl=True)
        with self.assertRaisesRegex(ValueError, "both user and assistant"):
            validate_source_approvals(self.data, self.manifest, include_jsonl=True)


if __name__ == "__main__":
    unittest.main()
