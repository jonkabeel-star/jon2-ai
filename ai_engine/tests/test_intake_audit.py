import json
import tempfile
import unittest
from pathlib import Path

from data_rights.intake_audit import audit_candidate


class IntakeAuditTests(unittest.TestCase):
    def test_txt_candidate_reports_hash_and_arabic_counts_without_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.txt"
            path.write_text("مرحبا بالعالم\nهذا نص أصلي\n", encoding="utf-8")
            report = audit_candidate(path)
        self.assertEqual(report["documents"], 2)
        self.assertGreater(report["language_signals"]["arabic_letters"], 0)
        self.assertEqual(report["rights_review"]["status"], "NOT_REVIEWED")
        self.assertFalse(report["rights_review"]["training_eligible"])
        self.assertFalse(report["side_effects"]["training_corpus_modified"])

    def test_jsonl_requires_text_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.jsonl"
            path.write_text(json.dumps({"prompt": "مرحبا"}, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "text"):
                audit_candidate(path)

    def test_malformed_jsonl_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Malformed JSONL"):
                audit_candidate(path)

    def test_invalid_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.txt"
            path.write_bytes(b"\\xff\\xfe")
            with self.assertRaises(UnicodeDecodeError):
                audit_candidate(path)

    def test_duplicate_documents_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.txt"
            path.write_text("مرحبا\n  مرحبا  \n", encoding="utf-8")
            report = audit_candidate(path)
        self.assertEqual(report["duplicate_signals"]["normalized_duplicate_groups"], 1)
        self.assertEqual(report["duplicate_signals"]["excess_duplicate_documents"], 1)

    def test_privacy_matches_are_counts_only(self):
        secret = "private.person@example.org"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.txt"
            path.write_text(f"تواصل مع {secret} أو 01012345678", encoding="utf-8")
            report = audit_candidate(path)
        rendered = json.dumps(report, ensure_ascii=False)
        self.assertEqual(report["privacy_signals"]["email_like_matches"], 1)
        self.assertEqual(report["privacy_signals"]["phone_like_matches"], 1)
        self.assertNotIn(secret, rendered)
        self.assertFalse(report["privacy_signals"]["matched_values_included"])

    def test_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "real.txt"
            target.write_text("نص", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this platform.")
            with self.assertRaisesRegex(ValueError, "symlink"):
                audit_candidate(link)

    def test_candidate_does_not_approve_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.txt"
            path.write_text("نص عربي", encoding="utf-8")
            report = audit_candidate(path)
        self.assertFalse(report["rights_review"]["training_eligible"])
        self.assertTrue(report["rights_review"]["human_approval_required"])
        self.assertFalse(report["side_effects"]["training_started"])


if __name__ == "__main__":
    unittest.main()
