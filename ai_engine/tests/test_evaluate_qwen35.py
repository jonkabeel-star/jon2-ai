"""CPU-only contract tests for the free Qwen3.5 evaluation path."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_engine.evaluate_qwen35 import DEFAULT_BENCHMARK, load_records, to_messages


class Qwen35EvaluationContractTests(unittest.TestCase):
    def test_held_out_benchmark_is_valid_and_unique(self):
        records = load_records(DEFAULT_BENCHMARK)
        self.assertGreaterEqual(len(records), 18)
        ids = [item["id"] for item in records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item.get("split") == "held_out" for item in records))

    def test_benchmark_contains_single_and_multi_turn_cases(self):
        records = load_records(DEFAULT_BENCHMARK)
        self.assertTrue(any("prompt" in item for item in records))
        multi_turn = [item for item in records if "turns" in item]
        self.assertGreaterEqual(len(multi_turn), 1)
        messages = to_messages(multi_turn[0])
        self.assertEqual(messages[-1]["role"], "user")
        self.assertGreaterEqual(len(messages), 2)

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            item = {"id": "same", "prompt": "مرحبا"}
            path.write_text(
                json.dumps(item, ensure_ascii=False) + "\n"
                + json.dumps(item, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_records(path)

    def test_rejects_records_with_both_prompt_and_turns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            item = {
                "id": "mixed",
                "prompt": "مرحبا",
                "turns": [{"role": "user", "content": "مرحبا"}],
            }
            path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                load_records(path)

    def test_rejects_conversation_that_does_not_end_with_user(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            item = {
                "id": "bad_turns",
                "turns": [
                    {"role": "user", "content": "سؤال"},
                    {"role": "assistant", "content": "رد"},
                ],
            }
            path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Last turn must be user"):
                load_records(path)

    def test_notebook_is_valid_and_has_gpu_and_release_guards(self):
        notebook_path = Path(__file__).resolve().parents[2] / "kaggle" / "qwen35-9b-free-evaluation.ipynb"
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        self.assertEqual(notebook.get("nbformat"), 4)
        self.assertTrue(notebook.get("cells"))
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        self.assertIn("torch.cuda.is_available()", source)
        self.assertIn("CPU fallback is disabled", source)
        self.assertIn("Qwen/Qwen3.5-9B", source)
        self.assertIn("eg_followup", source)
        self.assertIn("training_use':False", source)
        self.assertIn("jon2_qwen35_egyptian_evaluation.jsonl", source)


if __name__ == "__main__":
    unittest.main()
