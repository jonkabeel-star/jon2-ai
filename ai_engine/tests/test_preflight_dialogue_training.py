"""Tests for the read-only three-way dialogue preflight."""
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

from dialogue_split import prepare_approved_dialogue_splits
from preflight_dialogue_training import build_report


class DialoguePreflightTests(unittest.TestCase):
    def test_reports_capacity_blockers_without_using_held_out_test(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            source = data / "dialogues.jsonl"
            records = [
                {"messages": [
                    {"role": "user", "content": f"سؤال تجريبي مستقل رقم {i}"},
                    {"role": "assistant", "content": f"إجابة تجريبية مستقلة رقم {i}"},
                ]}
                for i in range(30)
            ]
            raw = "".join(
                json.dumps(record, ensure_ascii=False) + "\\n"
                for record in records
            ).encode("utf-8")
            source.write_bytes(raw)
            approval = data / "source_approvals.json"
            approval.write_text(json.dumps({"approved_sources": [{
                "file": source.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "character_count": len(raw.decode("utf-8")),
                "status": "APPROVED",
                "reviewer": "automated unit-test fixture",
                "review_date": "2026-11-25",
                "rights_basis": "synthetic test-only fixture",
                "intended_use": "research_training",
            }]}), encoding="utf-8")
            splits = root / "splits"
            prepare_approved_dialogue_splits(data, approval, splits, seed=17)
            report = build_report(
                data_dir=data,
                approval_manifest=approval,
                dialogue_splits_dir=splits,
                profile_name="arabic_30m",
            )
            self.assertFalse(report["readiness"]["ready"])
            self.assertIn("corpus_below_minimum_characters", report["readiness"]["blockers"])
            self.assertFalse(report["split_provenance"]["test_partition_used_for_training"])
            self.assertFalse(report["split_provenance"]["test_partition_used_for_checkpoint_selection"])
            self.assertEqual(report["split_provenance"]["partitions"]["test"]["file"], "test.jsonl")


if __name__ == "__main__":
    unittest.main()
