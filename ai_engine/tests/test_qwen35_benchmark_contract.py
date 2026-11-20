"""Contract tests for the private Qwen3.5 Arabic GPU workflow."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "Jon2_Qwen35_GPU_Inference_Training_Evaluation.ipynb"
BENCHMARK = ROOT / "ai_engine" / "evaluation" / "jon2_six_capability_pilot_v1.json"


class Qwen35BenchmarkContractTests(unittest.TestCase):
    def test_pilot_has_six_capabilities_and_ten_cases_each(self):
        cases = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        expected = {
            "intent_understanding",
            "natural_conversation",
            "context_tracking",
            "arabic_register",
            "reasoning",
            "personalization_privacy",
        }
        self.assertEqual({case["capability"] for case in cases}, expected)
        self.assertEqual(len(cases), 60)
        self.assertEqual(len({case["id"] for case in cases}), 60)
        for capability in expected:
            self.assertEqual(sum(c["capability"] == capability for c in cases), 10)

    def test_pilot_contains_egyptian_and_msa_and_valid_turns(self):
        cases = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        languages = {case.get("language") for case in cases}
        self.assertIn("eg", languages)
        self.assertIn("msa", languages)
        for case in cases:
            messages = case["messages"]
            self.assertTrue(messages)
            self.assertEqual(messages[-1]["role"], "user")
            self.assertTrue(all(m["role"] in {"user", "assistant"} for m in messages))
            self.assertTrue(all(messages[i]["role"] != messages[i - 1]["role"]
                                for i in range(1, len(messages))))
            self.assertTrue(case.get("rubric"))

    def test_training_and_evaluation_use_text_only_qwen_class(self):
        for path in (
            ROOT / "ai_engine" / "train_qwen35_lora.py",
            ROOT / "ai_engine" / "evaluate_qwen35_arabic.py",
            ROOT / "ai_engine" / "jon2_qwen35_server.py",
        ):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("Qwen3_5ForCausalLM", source)
                self.assertIn("AutoTokenizer", source)
                self.assertNotIn("Qwen3_5ForConditionalGeneration", source)
                self.assertNotIn("AutoProcessor", source)

    def test_kaggle_notebook_embedded_sources_match_repository(self):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cell = "".join(notebook["cells"][5]["source"])
        match = re.search(r"BUNDLED = json\.loads\(r'''([\s\S]*?)'''\)", cell)
        self.assertIsNotNone(match)
        bundled = json.loads(match.group(1))
        self.assertIn("ai_engine/train_qwen35_lora.py", bundled)
        self.assertIn("ai_engine/evaluate_qwen35_arabic.py", bundled)
        for relative_path, embedded in bundled.items():
            with self.subTest(path=relative_path):
                self.assertEqual(
                    embedded,
                    (ROOT / relative_path).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
