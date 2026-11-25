import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.audit_arabic_corpus import audit_splits


class ArabicCorpusAuditTests(unittest.TestCase):
    def write_split(self, root, name, rows):
        path = root / f"{name}.jsonl"
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_clean_text_splits_are_diagnostic_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا بالعالم", "document_id": "a"}]),
                "validation": self.write_split(root, "validation", [{"text": "كيف حالك اليوم", "document_id": "b"}]),
                "test": self.write_split(root, "test", [{"text": "هذا اختبار منفصل", "document_id": "c"}]),
            }
            report = audit_splits(paths, "text")
            self.assertEqual(report["total_records"], 3)
            self.assertEqual(report["blockers"], [])
            self.assertFalse(report["ready_for_training"])
            self.assertFalse(report["human_review"]["approved"])

    def test_empty_split_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا"}]),
                "validation": self.write_split(root, "validation", []),
                "test": self.write_split(root, "test", [{"text": "اختبار منفصل"}]),
            }
            report = audit_splits(paths, "text")
            self.assertIn("one_or_more_splits_are_empty", report["blockers"])

    def test_cross_split_duplicate_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا بالعالم"}]),
                "validation": self.write_split(root, "validation", [{"text": "مرحبا   بالعالم"}]),
                "test": self.write_split(root, "test", [{"text": "اختبار منفصل"}]),
            }
            report = audit_splits(paths, "text")
            self.assertIn("exact_normalized_content_leakage_across_splits", report["blockers"])

    def test_group_leakage_is_blocked_even_with_different_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا", "document_id": "same"}]),
                "validation": self.write_split(root, "validation", [{"text": "أهلا", "document_id": "same"}]),
                "test": self.write_split(root, "test", [{"text": "اختبار", "document_id": "other"}]),
            }
            report = audit_splits(paths, "text")
            self.assertIn("conversation_or_document_group_leakage_across_splits", report["blockers"])

    def test_group_leakage_report_never_exposes_raw_identifiers(self):
        secret_id = "PRIVATE-DOCUMENT-ID-987654"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا", "document_id": secret_id, "source_id": "src-a"}]),
                "validation": self.write_split(root, "validation", [{"text": "أهلا", "document_id": secret_id, "group_id": "grp-b"}]),
                "test": self.write_split(root, "test", [{"text": "اختبار", "document_id": "other"}]),
            }
            report_text = json.dumps(audit_splits(paths, "text"), ensure_ascii=False)
            self.assertNotIn(secret_id, report_text)
            self.assertNotIn("src-a", report_text)
            self.assertNotIn("grp-b", report_text)
            self.assertNotIn("group_id_sha256", report_text)
            self.assertNotIn("leakage_details", report_text)

    def test_all_group_fields_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "مرحبا", "document_id": "doc-a", "source_id": "source-shared"}]),
                "validation": self.write_split(root, "validation", [{"text": "أهلا", "document_id": "doc-b", "source_id": "source-shared"}]),
                "test": self.write_split(root, "test", [{"text": "اختبار", "document_id": "doc-c"}]),
            }
            report = audit_splits(paths, "text")
            self.assertIn("conversation_or_document_group_leakage_across_splits", report["blockers"])

    def test_possible_pii_is_flagged_without_echoing_raw_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "راسلني test@example.com"}]),
                "validation": self.write_split(root, "validation", [{"text": "نص عربي منفصل"}]),
                "test": self.write_split(root, "test", [{"text": "مثال آخر"}]),
            }
            report = audit_splits(paths, "text")
            self.assertIn("possible_personal_data_requires_manual_review", report["blockers"])
            self.assertNotIn("test@example.com", json.dumps(report, ensure_ascii=False))

    def test_dialogue_requires_alternating_user_assistant_turns(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"messages": [
                    {"role": "user", "content": "مرحبا"},
                    {"role": "assistant", "content": "أهلا"},
                ]}]),
                "validation": self.write_split(root, "validation", [{"messages": [
                    {"role": "user", "content": "كيف حالك"},
                    {"role": "assistant", "content": "بخير"},
                ]}]),
                "test": self.write_split(root, "test", [{"messages": [
                    {"role": "user", "content": "ما الأخبار"},
                    {"role": "assistant", "content": "جيدة"},
                ]}]),
            }
            report = audit_splits(paths, "dialogue")
            self.assertEqual(report["total_records"], 3)
            self.assertFalse(report["ready_for_training"])

    def test_dialogue_rejects_consecutive_same_role(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"messages": [
                    {"role": "user", "content": "مرحبا"},
                    {"role": "user", "content": "كيف حالك"},
                    {"role": "assistant", "content": "أهلا"},
                ]}]),
                "validation": self.write_split(root, "validation", [{"messages": [
                    {"role": "user", "content": "سؤال"},
                    {"role": "assistant", "content": "جواب"},
                ]}]),
                "test": self.write_split(root, "test", [{"messages": [
                    {"role": "user", "content": "سؤال آخر"},
                    {"role": "assistant", "content": "جواب آخر"},
                ]}]),
            }
            with self.assertRaisesRegex(ValueError, "alternate"):
                audit_splits(paths, "dialogue")


    def test_arabic_script_counts_and_tatweel_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "train": self.write_split(root, "train", [{"text": "الســــلام عليكم"}]),
                "validation": self.write_split(root, "validation", [{"text": "أهلا وسهلا"}]),
                "test": self.write_split(root, "test", [{"text": "اختبار مستقل"}]),
            }
            report = audit_splits(paths, "text")
            self.assertGreater(report["script_counts"]["arabic_characters"], 0)
            self.assertEqual(report["quality_flags"]["records_without_arabic_script"], 0)


if __name__ == "__main__":
    unittest.main()
