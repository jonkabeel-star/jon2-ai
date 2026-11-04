"""Unit tests for the real Jon2 chat runtime lifecycle."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
