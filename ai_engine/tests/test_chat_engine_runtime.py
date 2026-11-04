"""Unit tests for the real Jon2 chat runtime lifecycle."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chat_engine


class ChatEngineRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.original = (
            chat_engine._model,
            chat_engine._tokenizer,
            chat_engine._device,
            chat_engine.CHECKPOINT_PATH,
        )
        chat_engine._model = None
        chat_engine._tokenizer = None
        chat_engine._device = None

    def tearDown(self):
        (
            chat_engine._model,
            chat_engine._tokenizer,
            chat_engine._device,
            chat_engine.CHECKPOINT_PATH,
        ) = self.original

    def test_missing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            chat_engine.CHECKPOINT_PATH = Path(directory) / "missing.pt"
            self.assertFalse(chat_engine.checkpoint_is_available())
            with self.assertRaises(FileNotFoundError):
                chat_engine.load_runtime()
        self.assertFalse(chat_engine.model_is_ready())

    def test_runtime_loads_checkpoint_only_once(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "model.pt"
            checkpoint.write_bytes(b"test checkpoint placeholder")
            chat_engine.CHECKPOINT_PATH = checkpoint
            fake_runtime = (object(), object(), "cpu")
            with mock.patch.object(chat_engine, "load_model", return_value=fake_runtime) as loader:
                chat_engine.load_runtime()
                chat_engine.load_runtime()
            loader.assert_called_once_with(str(checkpoint))
            self.assertTrue(chat_engine.model_is_ready())
            self.assertEqual(chat_engine._device, "cpu")

    def test_empty_message_is_rejected_before_model_loading(self):
        with mock.patch.object(chat_engine, "load_runtime") as loader:
            with self.assertRaises(ValueError):
                chat_engine.generate_reply("   ")
        loader.assert_not_called()

    def test_conversation_prompt_includes_recent_context_and_current_turn(self):
        prompt = chat_engine.build_conversation_prompt(
            "ما اسمي؟",
            [
                {"role": "user", "content": "اسمي سامح"},
                {"role": "assistant", "content": "أهلًا سامح"},
            ],
        )
        self.assertEqual(
            prompt,
            "المستخدم: اسمي سامح\nJon2: أهلًا سامح\nالمستخدم: ما اسمي؟\nJon2:",
        )

    def test_conversation_prompt_uses_only_last_eight_turns(self):
        history = [
            {"role": "user", "content": f"رسالة {index}"}
            for index in range(10)
        ]
        prompt = chat_engine.build_conversation_prompt("الحالية", history)
        self.assertNotIn("رسالة 0", prompt)
        self.assertNotIn("رسالة 1", prompt)
        self.assertIn("رسالة 9", prompt)
        self.assertTrue(prompt.endswith("المستخدم: الحالية\nJon2:"))

    def test_reply_contains_only_generated_completion(self):
        prompt = "المستخدم: مرحبًا\nJon2:"
        chat_engine._model = object()
        chat_engine._tokenizer = object()
        chat_engine._device = "cpu"
        with mock.patch.object(chat_engine, "load_runtime"), \
             mock.patch.object(chat_engine, "generate", return_value=prompt + " أهلًا بك") as generator:
            answer = chat_engine.generate_reply("مرحبًا")
        self.assertEqual(answer, "أهلًا بك")
        self.assertEqual(generator.call_args.args[2], prompt)
        self.assertEqual(generator.call_args.kwargs["stop_sequences"], ["المستخدم:"])


if __name__ == "__main__":
    unittest.main()
