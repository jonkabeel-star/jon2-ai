"""Tests for the approved three-way dialogue-to-trainer boundary."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINE = Path(__file__).resolve().parents[1]
if str(AI_ENGINE) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE))

from dialogue_split import prepare_approved_dialogue_splits, load_jsonl
from dialogue_training import load_dialogue_training_partitions


class DialogueTrainingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "approved-data"
        self.data.mkdir()
        self.splits = self.root / "prepared-splits"
        self.source = self.data / "reviewed_dialogues.jsonl"
        self.records = [
            {"messages": [
                {"role": "user", "content": f"سؤال تدريبي مستقل رقم {i}"},
                {"role": "assistant", "content": f"إجابة تدريبية أصلية رقم {i}"},
            ]}
            for i in range(30)
        ]
        raw = "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in self.records
        ).encode("utf-8")
        self.source.write_bytes(raw)
        self.approvals = self.data / "source_approvals.json"
        approval = {
            "approved_sources": [{
                "file": self.source.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "character_count": len(raw.decode("utf-8")),
                "status": "APPROVED",
                "reviewer": "unit test fixture",
                "review_date": "2026-11-20",
                "rights_basis": "temporary synthetic test fixture",
                "intended_use": "research_training",
            }]
        }
        self.approvals.write_text(
            json.dumps(approval, ensure_ascii=False), encoding="utf-8"
        )
        self.split_report = prepare_approved_dialogue_splits(
            self.data, self.approvals, self.splits, seed=29
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_loader_returns_only_train_and_validation_text(self):
        train_text, validation_text, metadata = load_dialogue_training_partitions(
            self.splits, self.data, self.approvals
        )
        self.assertTrue(train_text.startswith("المستخدم:"))
        self.assertTrue(validation_text.startswith("المستخدم:"))
        self.assertNotEqual(train_text, validation_text)
        self.assertFalse(metadata["test_partition_used_for_training"])
        self.assertFalse(metadata["test_partition_used_for_checkpoint_selection"])
        self.assertEqual(
            set(metadata["partitions"]), {"train", "validation", "test"}
        )
        test_records = load_jsonl(self.splits / "test.jsonl")
        for record in test_records:
            for message in record["messages"]:
                self.assertNotIn(message["content"], train_text)
                self.assertNotIn(message["content"], validation_text)

    def test_changed_source_after_approval_blocks_training(self):
        self.source.write_text(
            self.source.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PermissionError, "changed after"):
            load_dialogue_training_partitions(
                self.splits, self.data, self.approvals
            )

    def test_modified_held_out_test_bytes_block_but_are_not_parsed(self):
        test_path = self.splits / "test.jsonl"
        test_path.write_bytes(b"not json and must not be decoded")
        with self.assertRaisesRegex(PermissionError, "test partition changed"):
            load_dialogue_training_partitions(
                self.splits, self.data, self.approvals
            )

    def test_manifest_hash_is_bound_into_candidate_metadata(self):
        _, _, metadata = load_dialogue_training_partitions(
            self.splits, self.data, self.approvals
        )
        manifest_raw = (self.splits / "split_manifest.json").read_bytes()
        self.assertEqual(
            metadata["split_manifest_sha256"],
            hashlib.sha256(manifest_raw).hexdigest(),
        )
        self.assertEqual(
            metadata["partitions"]["test"]["sha256"],
            self.split_report["partitions"]["test"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
