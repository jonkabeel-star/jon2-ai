"""Tests for conversation-level train/validation/test isolation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dialogue_split import split_dialogue_records, _record_group_fingerprints


def conversation(question, answer, follow_up=None, follow_answer=None):
    messages = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    if follow_up is not None:
        messages.extend([
            {"role": "user", "content": follow_up},
            {"role": "assistant", "content": follow_answer},
        ])
    return {"messages": messages}


class DialogueSplitTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            conversation(f"سؤال مستقل رقم {i}", f"إجابة مستقلة رقم {i}")
            for i in range(30)
        ]

    def test_deterministic(self):
        self.assertEqual(
            split_dialogue_records(self.records, seed=17),
            split_dialogue_records(self.records, seed=17),
        )

    def test_all_records_appear_exactly_once(self):
        parts = split_dialogue_records(self.records)
        self.assertEqual(sum(map(len, parts.values())), len(self.records))
        self.assertEqual(
            sum(len(part) for part in parts.values()),
            len({id(record) for part in parts.values() for record in part}),
        )

    def test_each_partition_is_nonempty(self):
        parts = split_dialogue_records(self.records)
        self.assertTrue(all(parts[name] for name in ("train", "validation", "test")))

    def test_conversations_are_never_fragmented(self):
        multi = conversation("سؤال متعدد", "إجابة أولى", "متابعة", "إجابة متابعة")
        parts = split_dialogue_records(self.records + [multi])
        found = [record for part in parts.values() for record in part if record is multi]
        self.assertEqual(len(found), 1)
        self.assertEqual(len(found[0]["messages"]), 4)

    def test_shared_normalized_question_links_records_into_one_partition(self):
        first = conversation("مَرْحَبًا يا Jon2", "الإجابة الأولى")
        second = conversation("مرحبا يا jon2", "الإجابة الثانية")
        parts = split_dialogue_records(self.records + [first, second])
        locations = {
            name for name, records in parts.items()
            if first in records or second in records
        }
        self.assertEqual(len(locations), 1)

    def test_shared_assistant_text_also_links_records(self):
        first = conversation("سؤال أول", "إجابة مشتركة")
        second = conversation("سؤال ثان", "إجابة مشتركة")
        parts = split_dialogue_records(self.records + [first, second])
        locations = {
            name for name, records in parts.items()
            if first in records or second in records
        }
        self.assertEqual(len(locations), 1)

    def test_shared_source_page_id_links_records_into_one_partition(self):
        first = conversation("سؤال صفحة أول", "إجابة أولى")
        second = conversation("سؤال صفحة ثان", "إجابة ثانية")
        first["source"] = {"dataset": "wikipedia-egyptian", "page_id": 1234}
        second["source"] = {"dataset": "wikipedia-egyptian", "page_id": 1234}
        parts = split_dialogue_records(self.records + [first, second])
        locations = {
            name for name, records in parts.items()
            if first in records or second in records
        }
        self.assertEqual(len(locations), 1)

    def test_same_page_id_from_different_datasets_does_not_link(self):
        first = conversation("سؤال صفحة أول", "إجابة أولى")
        second = conversation("سؤال صفحة ثان", "إجابة ثانية")
        first["source"] = {"dataset": "dataset-a", "page_id": 1234}
        second["source"] = {"dataset": "dataset-b", "page_id": 1234}
        self.assertNotEqual(
            _record_group_fingerprints(first, 0),
            _record_group_fingerprints(second, 1),
        )

    def test_too_few_independent_groups_fails_closed(self):
        records = [
            conversation("السؤال نفسه", "إجابة أ"),
            conversation("السؤال نفسه", "إجابة ب"),
            conversation("السؤال نفسه", "إجابة ج"),
        ]
        with self.assertRaisesRegex(ValueError, "three independent"):
            split_dialogue_records(records)

    def test_malformed_conversation_fails_closed(self):
        malformed = {"messages": [
            {"role": "user", "content": "سؤال"},
            {"role": "user", "content": "دور خاطئ"},
        ]}
        with self.assertRaisesRegex(ValueError, "expected assistant"):
            split_dialogue_records(self.records[:2] + [malformed])

    def test_empty_message_fails_closed(self):
        malformed = conversation("سؤال", " ")
        with self.assertRaisesRegex(ValueError, "empty"):
            split_dialogue_records(self.records[:2] + [malformed])


class ApprovedDialoguePreparationTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path

        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "training_data"
        self.data.mkdir()
        self.output = self.root / "prepared"
        self.source = self.data / "owner_dialogues.jsonl"
        self.records = [
            conversation(f"سؤال فريد رقم {i}", f"إجابة أصلية رقم {i}")
            for i in range(18)
        ]
        raw = "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in self.records
        )
        self.source.write_text(raw, encoding="utf-8")
        source_bytes = self.source.read_bytes()
        manifest = {
            "approved_sources": [{
                "file": "owner_dialogues.jsonl",
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "character_count": len(source_bytes.decode("utf-8")),
                "status": "APPROVED",
                "reviewer": "test reviewer",
                "review_date": "2026-11-20",
                "rights_basis": "temporary test fixture only",
                "intended_use": "research_training",
            }]
        }
        self.approvals = self.root / "source_approvals.json"
        self.approvals.write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_requires_exact_approval_and_writes_hash_manifest(self):
        from dialogue_split import prepare_approved_dialogue_splits, load_jsonl

        before = self.source.read_bytes()
        report = prepare_approved_dialogue_splits(
            self.data, self.approvals, self.output, seed=7
        )
        self.assertEqual(report["total_conversations"], 18)
        self.assertEqual(
            set(report["partitions"]), {"train", "validation", "test"}
        )
        self.assertTrue((self.output / "split_manifest.json").is_file())
        for name in ("train", "validation", "test"):
            self.assertTrue((self.output / f"{name}.jsonl").is_file())
            self.assertEqual(
                report["partitions"][name]["conversation_count"],
                len(load_jsonl(self.output / f"{name}.jsonl")),
            )
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse(report["model_training_started"])
        self.assertTrue(report["source_files_modified"] is False)

    def test_blocks_changed_source_after_approval(self):
        from dialogue_split import prepare_approved_dialogue_splits

        self.source.write_text(
            self.source.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PermissionError, "changed after"):
            prepare_approved_dialogue_splits(
                self.data, self.approvals, self.output
            )

    def test_output_must_be_outside_source_directory(self):
        from dialogue_split import prepare_approved_dialogue_splits

        with self.assertRaisesRegex(ValueError, "outside"):
            prepare_approved_dialogue_splits(
                self.data, self.approvals, self.data / "splits"
            )


if __name__ == "__main__":
    unittest.main()
