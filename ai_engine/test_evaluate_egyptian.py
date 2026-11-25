"""Unit tests for the Arabic human-review evaluation harness (no model required)."""
import json
import tempfile
import unittest
from pathlib import Path

from evaluate_egyptian import load_benchmark_cases, run_case


class FakeChatEngine:
    def __init__(self):
        self.calls = []
        self.answers = []

    def generate_reply(self, message, history=None):
        self.calls.append({"message": message, "history": [dict(item) for item in (history or [])]})
        answer = f"رد على: {message}" if not self.answers else self.answers.pop(0)
        return answer


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

    def test_multi_turn_case_passes_prior_model_turns_to_runtime(self):
        engine = FakeChatEngine()
        engine.answers = ["إجابة Jon2 الأولى", "إجابة Jon2 الثانية"]
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
        self.assertEqual(
            engine.calls[1]["history"],
            [
                {"role": "user", "content": "عايز أتعلم بايثون"},
                {"role": "assistant", "content": "إجابة Jon2 الأولى"},
            ],
        )
        self.assertEqual(result["answer"], "إجابة Jon2 الثانية")
        self.assertNotIn("ابدأ بالأساسيات", [turn["content"] for turn in result["conversation"]])
        self.assertEqual(len(result["generated_turns"]), 2)

    def test_single_turn_result_contains_prompt_and_generated_answer(self):
        engine = FakeChatEngine()
        engine.answers = ["إجابة حقيقية من Jon2"]
        result = run_case(engine, {"prompt": "إزيك؟"})
        self.assertEqual(result["answer"], "إجابة حقيقية من Jon2")
        self.assertEqual(
            result["conversation"],
            [
                {"role": "user", "content": "إزيك؟"},
                {"role": "assistant", "content": "إجابة حقيقية من Jon2"},
            ],
        )

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

    def test_non_alternating_conversation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-turns.jsonl"
            record = {
                "id": "bad-turns",
                "turns": [
                    {"role": "user", "content": "سؤال أول"},
                    {"role": "user", "content": "سؤال ثان"},
                ],
                "review_criteria": "اختبار",
                "split": "held_out",
                "language": "Egyptian Arabic",
            }
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_benchmark_cases(path)


if __name__ == "__main__":
    unittest.main()
