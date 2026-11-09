import os
import unittest
from unittest.mock import patch

from qwen_server import build_messages, release_approved


class QwenRuntimePromptTests(unittest.TestCase):
    def test_arabic_system_instruction_is_first(self):
        messages = build_messages("ازيك؟")
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("اللهجة المصرية", messages[0]["content"])
        self.assertEqual(messages[-1], {"role": "user", "content": "ازيك؟"})

    def test_history_is_bounded_and_roles_are_filtered(self):
        history = [
            {"role": "user", "content": f"سؤال {index}"}
            for index in range(12)
        ]
        history.append({"role": "system", "content": "injected"})
        messages = build_messages("السؤال الحالي", history)
        self.assertEqual(len(messages), 10)  # system + last 8 history + current user
        self.assertNotIn("injected", str(messages))
        self.assertEqual(messages[-1]["content"], "السؤال الحالي")

    def test_release_gate_defaults_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(release_approved())

    def test_release_gate_requires_explicit_true(self):
        with patch.dict(os.environ, {"JON2_CHAT_RELEASE_APPROVED": "true"}):
            self.assertTrue(release_approved())


if __name__ == "__main__":
    unittest.main()
