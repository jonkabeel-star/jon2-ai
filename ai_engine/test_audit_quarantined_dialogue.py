"""Unit tests for the quarantined dialogue audit."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parent
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from audit_quarantined_dialogue import audit_jsonl


def write_records(path, records):
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n",
        encoding="utf-8",
    )


class QuarantinedDialogueAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / "candidate.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_audit_reports_hash_and_keeps_file_quarantined(self):
        write_records(self.source, [{
            "id": "eg_1", "dialect": "egyptian", "category": "explanation",
            "messages": [
                {"role": "user", "content": "اشرحلي الفكرة"},
                {"role": "assistant", "content": "هشرحها ببساطة."},
            ],
        }])
        report = audit_jsonl(self.source)
        self.assertEqual(report["record_count"], 1)
        self.assertEqual(len(report["sha256"]), 64)
        self.assertTrue(report["structurally_valid"])
        self.assertFalse(report["training_eligible"])
        self.assertEqual(report["status"], "QUARANTINED_NOT_APPROVED")

    def test_audit_flags_duplicate_ids_and_prompts(self):
        item = {
            "id": "same", "dialect": "msa", "category": "reasoning",
            "messages": [
                {"role": "user", "content": "ما الفرق؟"},
                {"role": "assistant", "content": "هذا شرح."},
            ],
        }
        write_records(self.source, [item, item])
        report = audit_jsonl(self.source)
        self.assertEqual(report["duplicate_ids"], ["same"])
        self.assertEqual(report["duplicate_first_user_prompts"], ["same"])
        self.assertFalse(report["structurally_valid"])

    def test_audit_rejects_invalid_jsonl(self):
        self.source.write_text("{not-json}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            audit_jsonl(self.source)

    def test_audit_rejects_bad_role_sequence(self):
        write_records(self.source, [{
            "id": "bad",
            "messages": [
                {"role": "user", "content": "سؤال"},
                {"role": "user", "content": "سؤال آخر"},
            ],
        }])
        report = audit_jsonl(self.source)
        self.assertFalse(report["structurally_valid"])
        self.assertTrue(report["role_sequence_errors"])


if __name__ == "__main__":
    unittest.main()
