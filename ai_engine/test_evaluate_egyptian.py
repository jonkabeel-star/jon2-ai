"""Unit tests for the Arabic human-review evaluation harness (no model required)."""
import json
import tempfile
import unittest
from pathlib import Path

from evaluate_egyptian import load_benchmark_cases, run_case


class FakeChatEngine:
    def __init__(self):
        self.calls = []

    def generate_reply(self, message, history=None):
        self.calls.append({"message": message, "history": list(history or [])})
        return f"رد على: {message}"


class ArabicBenchmarkTests(unittest.TestCase):
    def test_egyptian_repository_benchmark_loads_and_contains_multi_turn_cases(self):
        path = Path(__file__).resolve().parent / "evaluation" / "egyptian_arabic_prompts.jsonl"
        cases = load_benchmark_cases(path)
        self.assertEqual(len(cases), 20)
        self.assertTrue(any("turns" in case for case in cases))
        self.assertTrue(all(case["language"] == "Egyptian Arabic" for case in cases))

    def test_msa_repository_benchmark_loads_and_contains_multi_turn_cases(self):
        path = Path(__file__).resolve().parent / "evaluation" / "msa_arabic_prompts.jsonl"
        cases = load_benchmark_cases(path, expected_language="Modern Standard Arabic")
        self.assertEqual(len(cases), 20)
        self.assertTrue(any("turns" in case for case in cases))
        self.assertTrue(all(case["language"] == "Modern Standard Arabic" for case in cases))

    def test_multi_turn_case_passes_prior_turns_to_runtime(self):
        engine = FakeChatEngine()
        item = {
            "id": "multi",
            "turns": [
                {"role": "user", "content": "عايز أتعلم بايثون"},
                {"role": "assistant", "content": "ابدأ بالأساسيات"},
                {"role": "user", "content": "أبدأ بإيه؟"},
            ],
        }
        result = run_case(engine, item)
        self.assertEqual(len(engine.calls), 2)
        self.assertEqual(engine.calls[1]["message"], "أبدأ بإيه؟")
        self.assertEqual(engine.calls[1]["history"][0]["content"], "عايز أتعلم بايثون")
        self.assertEqual(engine.calls[1]["history"][1]["content"], "رد على: عايز أتعلم بايثون")
        self.assertIn("answer", result)

    def test_language_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong-language.jsonl"
            record = {
                "id": "wrong",
                "prompt": "مرحبًا",
                "review_criteria": "رد واضح",
                "split": "held_out",
                "language": "Egyptian Arabic",
            }
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_benchmark_cases(path, expected_language="Modern Standard Arabic")

    def test_unsupported_expected_language_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_benchmark_cases(path, expected_language="English")

    def test_invalid_record_with_prompt_and_turns_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            record = {
                "id": "bad",
                "prompt": "سؤال",
                "turns": [{"role": "user", "content": "سؤال"}],
                "review_criteria": "اختبار",
                "split": "held_out",
                "language": "Egyptian Arabic",
            }
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_benchmark_cases(path)


if __name__ == "__main__":
    unittest.main()
