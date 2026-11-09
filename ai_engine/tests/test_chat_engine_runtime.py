"""Unit tests for the real Jon2 chat runtime lifecycle."""
import sys
import tempfile
import unittest

import torch
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
        self.assertTrue(prompt.startswith("تعليمات: أجب بعربية سهلة وواضحة."))
        self.assertIn("المستخدم: اسمي سامح", prompt)
        self.assertIn("Jon2: أهلًا سامح", prompt)
        self.assertTrue(prompt.endswith("المستخدم: ما اسمي؟\nJon2:"))

    def test_conversation_prompt_preserves_complete_recent_messages(self):
        previous = "هذه رسالة سابقة مهمة " * 20
        prompt = chat_engine.build_conversation_prompt(
            "تابع من فضلك",
            [{"role": "user", "content": previous}],
        )
        self.assertIn(previous, prompt)

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

    def test_checkpoint_loader_uses_safe_torch_deserialization(self):
        import jon2_core

        tokenizer = mock.Mock(vocab_size=32)
        model = mock.Mock()
        model.to.return_value = model
        checkpoint = {
            "tokenizer": {},
            "config": {},
            "model_state": {},
        }
        with mock.patch.object(
            jon2_core.torch, "load", return_value=checkpoint
        ) as loader, mock.patch.object(
            jon2_core.ByteBPETokenizer, "from_dict", return_value=tokenizer
        ), mock.patch.object(
            jon2_core, "Jon2Transformer", return_value=model
        ):
            loaded_model, loaded_tokenizer, device = jon2_core.load_model(
                "checkpoint.pt", device="cpu"
            )

        loader.assert_called_once_with(
            "checkpoint.pt", map_location=torch.device("cpu"), weights_only=True
        )
        self.assertIs(loaded_model, model)
        self.assertIs(loaded_tokenizer, tokenizer)
        self.assertEqual(device.type, "cpu")

    def test_reply_uses_deterministic_low_noise_generation_settings(self):
        chat_engine._model = object()
        chat_engine._tokenizer = object()
        chat_engine._device = "cpu"
        with (
            mock.patch.object(chat_engine, "load_runtime"),
            mock.patch.object(
                 chat_engine,
                 "generate",
                 side_effect=lambda *args, **kwargs: args[2] + " أهلًا بك",
            ) as generator,
        ):
            answer = chat_engine.generate_reply("مرحبًا")
        self.assertEqual(answer, "أهلًا بك")
        self.assertFalse(generator.call_args.kwargs["do_sample"])
        self.assertEqual(generator.call_args.kwargs["repetition_penalty"], 1.10)
        self.assertEqual(generator.call_args.kwargs["no_repeat_ngram_size"], 3)
        self.assertEqual(generator.call_args.kwargs["top_k"], 0)

    def test_reply_contains_only_generated_completion(self):
        chat_engine._model = object()
        chat_engine._tokenizer = object()
        chat_engine._device = "cpu"
        with mock.patch.object(chat_engine, "load_runtime"), \\
             mock.patch.object(
                 chat_engine,
                 "generate",
                 side_effect=lambda *args, **kwargs: args[2] + " أهلًا بك",
             ) as generator:
            answer = chat_engine.generate_reply("مرحبًا")
        self.assertEqual(answer, "أهلًا بك")
        self.assertIn("تعليمات: أجب بالعربية الواضحة", generator.call_args.args[2])
        self.assertEqual(generator.call_args.kwargs["stop_sequences"], ["المستخدم:"])

if __name__ == "__main__":
    unittest.main()
