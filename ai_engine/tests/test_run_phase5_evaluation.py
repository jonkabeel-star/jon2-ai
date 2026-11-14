"""Tests for Phase 5 private-checkpoint evaluation safeguards."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_phase5_evaluation import load_phase5_prompts, sha256_file


class PhaseFiveRunnerTests(unittest.TestCase):
    def test_repository_benchmark_passes_strict_validation(self):
        path = Path(__file__).resolve().parents[1] / "evaluation" / "phase5_prompts_100.jsonl"
        rows = load_phase5_prompts(path)
        self.assertEqual(len(rows), 100)
        self.assertEqual(sum(row["language"] == "msa" for row in rows), 50)
        self.assertEqual(sum(row["language"] == "egyptian" for row in rows), 50)

    def test_rejects_non_heldout_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            rows = [
                {"id": f"msa-{i}", "prompt": "سؤال", "language": "msa",
                 "split": "evaluation_only", "training_eligible": False}
                for i in range(50)
            ] + [
                {"id": f"egy-{i}", "prompt": "سؤال", "language": "egyptian",
                 "split": "train", "training_eligible": False}
                for i in range(50)
            ]
            path.write_text("\\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not explicitly held out"):
                load_phase5_prompts(path)

    def test_checkpoint_fingerprint_is_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.bin"
            path.write_bytes(b"private checkpoint bytes")
            digest = sha256_file(path)
            self.assertEqual(len(digest), 64)
            self.assertTrue(all(char in "0123456789abcdef" for char in digest))


if __name__ == "__main__":
    unittest.main()
