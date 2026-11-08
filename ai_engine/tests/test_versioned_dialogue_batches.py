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

    def test_all_project_dialogue_batches_are_registered_with_correct_approval_status(self):
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
                self.assertIn("approved for private experimental research training only", row.casefold())

                marker = f"training_data/{batch.name}"
                self.assertIn(marker, register, f"{batch.name} is missing from DATASET_REGISTER.md")
                if batch.name == "original_dialogue_ar_batch_04.txt":
                    self.assertIn("APPROVED FOR PRIVATE EXPERIMENTAL RESEARCH TRAINING ONLY", register)
                else:
                    approval_section = register.split("## Verified first training experiment", 1)[-1]
                    self.assertIn(marker, approval_section, f"{batch.name} is missing from the exact-file approval record")

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
