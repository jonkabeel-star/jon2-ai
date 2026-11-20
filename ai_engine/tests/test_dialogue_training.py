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
from train_jon2 import _training_plan


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
        test_text = "\n".join(
            message["content"]
            for record in test_records
            for message in record["messages"]
        )
        self.assertNotIn(test_text, train_text)
        self.assertNotIn(test_text, validation_text)

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

    def test_manifest_hash_is_bound_into_training_plan(self):
        _, _, metadata = load_dialogue_training_partitions(
            self.splits, self.data, self.approvals
        )
        import argparse
        args = argparse.Namespace(
            steps=10, batch_size=2, context=8, width=16, heads=2, layers=1,
            dropout=0.0, learning_rate=0.001, weight_decay=0.01,
            warmup_steps=1, validation_fraction=0.1, eval_steps=1,
            eval_every=1, patience=2, min_delta=0.0, grad_clip=1.0,
            minimum_chars=1_000_000, tokenizer_vocab_size=300,
            tokenizer_min_frequency=1, seed=29, no_amp=True,
            dialogue_splits_dir=str(self.splits),
            dialogue_split_manifest_sha256=metadata["split_manifest_sha256"],
        )
        plan = _training_plan(args)
        self.assertEqual(
            plan["validation_split_algorithm"],
            "approved_jsonl_conversation_three_way_v1",
        )
        self.assertEqual(
            plan["dialogue_split_manifest_sha256"],
            metadata["split_manifest_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
