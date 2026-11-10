"""Tests for the safe Jon2 autonomous brain-builder controller."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomous_builder import (
    _recommendations,
    _safe_report_destination,
    _write_report_atomically,
    build_autonomous_report,
)


class AutonomousBuilderTests(unittest.TestCase):
    def test_missing_approval_fails_closed_without_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "training_data"
            data.mkdir()
            (data / "sample.txt").write_text("نص تجريبي\n", encoding="utf-8")
            report = build_autonomous_report(
                root, Path("training_data"), Path("training_data/source_approvals.json")
            )
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["source_approval"]["passed"])
        self.assertFalse(report["training_started"])
        self.assertFalse(report["model_weights_changed"])
        self.assertIn("source_approval_required", report["blockers"])

    def test_recommendations_prioritize_rights_and_data_volume(self):
        tasks = _recommendations(
            ["insufficient_tokens_per_parameter"], approval_ok=False
        )
        self.assertEqual(tasks[0]["priority"], "critical")
        self.assertTrue(any("Expand the corpus" in task["task"] for task in tasks))

    def test_report_destination_must_be_outside_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with self.assertRaises(ValueError):
                _safe_report_destination(root / "report.json", root)
            outside = root.parent / (root.name + "-report.json")
            self.assertEqual(_safe_report_destination(outside, root), outside.resolve())

    def test_report_destination_rejects_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "repo"
            root.mkdir()
            protected = workspace / "protected.txt"
            protected.write_text("keep me", encoding="utf-8")
            destination = workspace / "report.json"
            destination.symlink_to(protected)
            with self.assertRaises(ValueError):
                _safe_report_destination(destination, root)
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep me")
            self.assertTrue(destination.is_symlink())

    def test_report_writer_ignores_preexisting_temp_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "repo"
            output = workspace / "output"
            root.mkdir()
            output.mkdir()
            destination = output / "report.json"
            protected = output / "protected.txt"
            protected.write_text("keep me", encoding="utf-8")
            stale_temp = destination.with_name(destination.name + ".tmp")
            stale_temp.symlink_to(protected)

            safe_destination = _safe_report_destination(destination, root)
            _write_report_atomically(safe_destination, '{"status": "blocked"}\\n')

            self.assertEqual(protected.read_text(encoding="utf-8"), "keep me")
            self.assertTrue(stale_temp.is_symlink())
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                '{"status": "blocked"}\\n',
            )

    def test_no_automatic_training_or_release_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            report = build_autonomous_report(
                root, Path("data"), Path("data/approvals.json")
            )
        self.assertIn("start model training or fine-tuning", report["never_automatic_actions"])
        self.assertFalse(report["public_release_approved"])


if __name__ == "__main__":
    unittest.main()
