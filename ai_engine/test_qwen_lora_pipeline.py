import json
import tempfile
import unittest
from pathlib import Path

from finetune_qwen_lora import (
    collect_conversations,
    load_approved_dialogue_files,
    parse_dialogue_text,
    sha256_bytes,
    split_conversations,
)


class DialogueParserTests(unittest.TestCase):
    def test_parses_arabic_user_assistant_pair(self):
        rows = parse_dialogue_text("المستخدم: ازيك؟\nJon2: الحمد لله، أهلاً بيك.")
        self.assertEqual(rows[0][0]["role"], "user")
        self.assertEqual(rows[0][1]["role"], "assistant")
        self.assertEqual(rows[0][1]["content"], "الحمد لله، أهلاً بيك.")

    def test_rejects_unpaired_or_reversed_turns(self):
        with self.assertRaises(ValueError):
            parse_dialogue_text("المستخدم: سؤال فقط")
        with self.assertRaises(ValueError):
            parse_dialogue_text("Jon2: رد قبل السؤال")

    def test_rejects_unknown_lines_instead_of_silently_dropping_them(self):
        with self.assertRaises(ValueError):
            parse_dialogue_text("المستخدم: سؤال\nهذا سطر غير مصنف")

    def test_rejects_email_addresses(self):
        with self.assertRaisesRegex(ValueError, "email"):
            parse_dialogue_text("المستخدم: راسلني user@example.com\nJon2: لا تشارك بياناتك الخاصة.")

    def test_rejects_egyptian_mobile_numbers(self):
        with self.assertRaisesRegex(ValueError, "mobile"):
            parse_dialogue_text("المستخدم: رقمي 01012345678\nJon2: لا تشارك رقمك.")

    def test_rejects_credential_like_text(self):
        with self.assertRaisesRegex(ValueError, "credential"):
            parse_dialogue_text("المستخدم: api_key=AbCdEf1234567890\nJon2: لا تشارك المفاتيح السرية.")

    def test_deduplicates_exact_conversations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "original_dialogue_ar.txt"
            path.write_text(
                "المستخدم: سؤال\nJon2: إجابة\n\nالمستخدم: سؤال\nJon2: إجابة",
                encoding="utf-8",
            )
            self.assertEqual(len(collect_conversations([path])), 1)

    def test_split_is_deterministic_and_three_way_disjoint(self):
        conversations = [
            [{"role": "user", "content": f"سؤال {i}"}, {"role": "assistant", "content": f"جواب {i}"}]
            for i in range(100)
        ]
        train_a, val_a, test_a = split_conversations(conversations, 0.1, 0.1, 42)
        train_b, val_b, test_b = split_conversations(conversations, 0.1, 0.1, 42)
        self.assertEqual((train_a, val_a, test_a), (train_b, val_b, test_b))
        self.assertEqual(len(train_a) + len(val_a) + len(test_a), 100)
        train_set, val_set, test_set = map(lambda rows: set(map(str, rows)), (train_a, val_a, test_a))
        self.assertFalse(train_set & val_set)
        self.assertFalse(train_set & test_set)
        self.assertFalse(val_set & test_set)

    def test_split_rejects_small_corpus(self):
        with self.assertRaisesRegex(ValueError, "at least 20"):
            split_conversations([[{"role": "user", "content": "س"} , {"role": "assistant", "content": "ج"}]] * 10)


class RightsApprovalTests(unittest.TestCase):
    def make_approval(self, text):
        return {
            "file": "original_dialogue_ar.txt",
            "sha256": sha256_bytes(text.encode("utf-8")),
            "character_count": len(text),
            "status": "APPROVED",
            "reviewer": "Human reviewer",
            "review_date": "2026-11-09",
            "rights_basis": "Original project-authored material with documented owner authorization.",
            "intended_use": "research_training",
        }

    def test_accepts_exact_approved_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            content = "المستخدم: سؤال\nJon2: إجابة"
            (data / "original_dialogue_ar.txt").write_text(content, encoding="utf-8")
            manifest = root / "approvals.json"
            manifest.write_text(json.dumps({"approved_sources": [self.make_approval(content)]}), encoding="utf-8")
            files, hashes = load_approved_dialogue_files(data, manifest)
            self.assertEqual([p.name for p in files], ["original_dialogue_ar.txt"])
            self.assertEqual(hashes["original_dialogue_ar.txt"], sha256_bytes(content.encode("utf-8")))

    def test_rejects_changed_source_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            approved = "المستخدم: سؤال\nJon2: إجابة"
            (data / "original_dialogue_ar.txt").write_text(approved + " تعديل", encoding="utf-8")
            manifest = root / "approvals.json"
            manifest.write_text(json.dumps({"approved_sources": [self.make_approval(approved)]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_approved_dialogue_files(data, manifest)

    def test_rejects_candidate_only_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            content = "المستخدم: سؤال\nJon2: إجابة"
            (data / "original_dialogue_ar.txt").write_text(content, encoding="utf-8")
            candidate = self.make_approval(content)
            candidate["status"] = "candidate_only"
            manifest = root / "approvals.json"
            manifest.write_text(json.dumps({"approved_sources": [candidate]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unapproved"):
                load_approved_dialogue_files(data, manifest)


if __name__ == "__main__":
    unittest.main()
