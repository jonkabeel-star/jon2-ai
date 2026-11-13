"""Tests for held-out evaluation prompt validation."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_model import load_prompts, REVIEW_DIMENSIONS, main


class EvaluationPromptTests(unittest.TestCase):
    def test_loads_valid_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text(
                json.dumps({"id": "one", "prompt": "سؤال"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(load_prompts(path), [{"id": "one", "prompt": "سؤال"}])

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            item = json.dumps({"id": "same", "prompt": "سؤال"})
            path.write_text(item + "\n" + item + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_prompts(path)

    def test_rejects_empty_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text(json.dumps({"id": "one", "prompt": " "}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                load_prompts(path)

    def test_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid JSON"):
                load_prompts(path)

    def test_requires_nonempty_evaluation_set(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prompts.jsonl"
            path.write_text("# held out prompts only\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty"):
                load_prompts(path)

    def test_review_rubric_has_six_dimensions(self):
        self.assertEqual(len(REVIEW_DIMENSIONS), 6)
        self.assertIn("arabic_quality", REVIEW_DIMENSIONS)

    def test_repository_heldout_set_has_forty_unique_prompts(self):
        prompt_path = Path(__file__).resolve().parents[1] / "evaluation" / "prompts_ar.jsonl"
        prompts = load_prompts(prompt_path)
        self.assertEqual(len(prompts), 40)
        self.assertEqual(len({item["id"] for item in prompts}), 40)


    def test_evaluator_uses_dialogue_stop_marker(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "trained.pt"
            checkpoint.write_bytes(b"checkpoint placeholder")
            prompts = root / "prompts.jsonl"
            prompts.write_text(
                json.dumps({"id": "one", "prompt": "سؤال"}) + "\n",
                encoding="utf-8",
            )
            output = root / "report.json"
            with patch(
                "evaluate_model.load_model",
                return_value=(object(), object(), "cpu"),
            ):
                with patch(
                    "evaluate_model.generate",
                    return_value="المستخدم: سؤال\nJon2:إجابة",
                ) as generator:
                    with patch("sys.argv", [
                        "evaluate_model.py", "--checkpoint", str(checkpoint),
                        "--prompts", str(prompts), "--output", str(output),
                    ]):
                        with redirect_stdout(StringIO()):
                            self.assertEqual(main(), 0)
            self.assertEqual(generator.call_args.kwargs["stop_sequences"], ["المستخدم:"])
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["checkpoint_sha256"], __import__("hashlib").sha256(b"checkpoint placeholder").hexdigest())
            self.assertFalse(report["release_approved"])
            self.assertIsNone(report["automated_quality_verdict"])


    def test_cli_rejects_checkpoint_fingerprint_mismatch_before_loading(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "trained.pt"
            checkpoint.write_bytes(b"real checkpoint bytes")
            prompts = root / "prompts.jsonl"
            prompts.write_text(
                json.dumps({"id": "one", "prompt": "سؤال"}) + "\\n",
                encoding="utf-8",
            )
            with patch("evaluate_model.load_model") as loader:
                with patch("sys.argv", [
                    "evaluate_model.py", "--checkpoint", str(checkpoint),
                    "--prompts", str(prompts), "--checkpoint-sha256", "0" * 64,
                ]):
                    with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                        main()
                loader.assert_not_called()

    def test_cli_refuses_missing_checkpoint(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not-trained.pt"
            with patch("sys.argv", ["evaluate_model.py", "--checkpoint", str(missing)]):
                with redirect_stdout(StringIO()):
                    self.assertEqual(main(), 2)


if __name__ == "__main__":
    unittest.main()
