from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "hybrid_training" / "train_full.py"

# Parser tests need no GPU and no PyTorch installation. The training script
# imports torch at module load; provide a harmless stub only when torch is
# absent. These tests never call training functions.
try:
    import torch  # noqa: F401
except ModuleNotFoundError:
    sys.modules["torch"] = types.ModuleType("torch")

spec = importlib.util.spec_from_file_location("jon2_train_full", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class DialogueParserTests(unittest.TestCase):
    def test_skips_metadata_comments_and_parses_pairs(self):
        source = """# Project-authored data
# Format: alternating turns

المستخدم: صباح الخير
Jon2: صباح النور
المستخدم: كيف حالك؟
Jon2: أنا بخير
"""
        conversations = module.parse_txt_dialogue(source, "sample.txt")
        self.assertEqual(len(conversations), 2)
        self.assertEqual(conversations[0][0]["content"], "صباح الخير")
        self.assertEqual(conversations[1][1]["content"], "أنا بخير")

    def test_preserves_multiline_assistant_answer(self):
        source = """المستخدم: اشرح الفكرة
Jon2: الجملة الأولى.
الجملة الثانية.
"""
        conversations = module.parse_txt_dialogue(source, "sample.txt")
        self.assertEqual(conversations[0][1]["content"], "الجملة الأولى.\nالجملة الثانية.")

    def test_rejects_unlabeled_prose(self):
        with self.assertRaises(ValueError):
            module.parse_txt_dialogue("نص غير موسوم", "sample.txt")

    def test_rejects_assistant_before_user(self):
        with self.assertRaises(ValueError):
            module.parse_txt_dialogue("Jon2: إجابة بلا سؤال", "sample.txt")

    def test_rejects_unanswered_final_user_turn(self):
        with self.assertRaises(ValueError):
            module.parse_txt_dialogue("المستخدم: سؤال بلا إجابة", "sample.txt")


if __name__ == "__main__":
    unittest.main()
