"""Regression tests for the Jon2 training-data structure audit."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_data import audit_dialogue, is_dialogue_file


class DialogueBatchAuditTests(unittest.TestCase):
    def test_versioned_arabic_dialogue_batch_is_recognized(self):
        self.assertTrue(is_dialogue_file(Path("original_dialogue_ar_batch_01.txt")))
        self.assertTrue(is_dialogue_file(Path("original_dialogue_ar.txt")))
        self.assertFalse(is_dialogue_file(Path("original_seed_ar.txt")))
        self.assertFalse(is_dialogue_file(Path("original_dialogue_ar_batch_01.jsonl")))

    def test_all_project_dialogue_batches_are_registered_and_unapproved(self):
        repository = Path(__file__).resolve().parents[2]
        training_dir = repository / "ai_engine" / "training_data"
        readme = (training_dir / "README.md").read_text(encoding="utf-8")
        register = (repository / "ai_engine" / "DATASET_REGISTER.md").read_text(encoding="utf-8")
        batches = sorted(training_dir.glob("original_dialogue_ar_batch_*.txt"))
        self.assertGreaterEqual(len(batches), 3)

        for batch in batches:
            with self.subTest(batch=batch.name):
                row = next((line for line in readme.splitlines() if batch.name in line), "")
                self.assertTrue(row, f"{batch.name} is missing from training_data/README.md")
                self.assertIn("not approved", row.casefold())

                marker = f"`{batch.name}`"
                position = register.find(marker)
                self.assertNotEqual(position, -1, f"{batch.name} is missing from DATASET_REGISTER.md")
                section_start = register.rfind("\n## Candidate", 0, position)
                section_end = register.find("\n## Candidate", position + len(marker))
                section = register[section_start:section_end if section_end >= 0 else None]
                status_lines = [line for line in section.splitlines() if line.startswith("- Status:")]
                self.assertTrue(status_lines, f"{batch.name} has no register status")
                self.assertIn("NOT APPROVED", status_lines[0].upper())

    def test_valid_alternating_dialogue_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar_batch_01.txt"
            path.write_text(
                "# draft header\n\nالمستخدم: مرحبًا\nJon2: أهلًا بك\n",
                encoding="utf-8",
            )
            self.assertEqual(audit_dialogue(path), [])

    def test_invalid_speaker_order_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar_batch_01.txt"
            path.write_text(
                "Jon2: إجابة بلا سؤال\nالمستخدم: سؤال متأخر\n",
                encoding="utf-8",
            )
            errors = audit_dialogue(path)
            self.assertEqual(len(errors), 2)

    def test_unmatched_turn_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "original_dialogue_ar_batch_01.txt"
            path.write_text("المستخدم: سؤال بلا إجابة\n", encoding="utf-8")
            self.assertEqual(len(audit_dialogue(path)), 1)


if __name__ == "__main__":
    unittest.main()
