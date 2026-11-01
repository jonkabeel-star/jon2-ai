import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit_corpus.py")


class CorpusAuditTests(unittest.TestCase):
    def test_supported_messages_schema(self):
        from audit_corpus import extract_record
        user, assistant = extract_record({
            "messages": [
                {"role": "user", "content": "مرحبا"},
                {"role": "assistant", "content": "أهلا"},
            ]
        })
        self.assertEqual(user, "مرحبا")
        self.assertEqual(assistant, "أهلا")

    def test_supported_prompt_response_schema(self):
        from audit_corpus import extract_record
        self.assertEqual(extract_record({"prompt": "سؤال", "response": "جواب"}), ("سؤال", "جواب"))

    def test_report_does_not_print_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train = root / "train.jsonl"
            test = root / "test.jsonl"
            train.write_text(json.dumps({"prompt": "SECRET_USER_TEXT", "response": "SECRET_ASSISTANT_TEXT"}) + "\n", encoding="utf-8")
            test.write_text(json.dumps({"prompt": "سؤال مختلف", "response": "إجابة مختلفة"}) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--train", str(train), "--test", str(test),
                 "--min-train-records", "1", "--min-train-characters", "1"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotIn("SECRET_USER_TEXT", result.stdout)
            self.assertNotIn("SECRET_ASSISTANT_TEXT", result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["train"]["records"], 1)
            self.assertEqual(report["exact_train_test_overlap"], 0)


if __name__ == "__main__":
    unittest.main()
