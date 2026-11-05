"""Offline contract tests for the local-only Jais 2 adapter.

These tests do not download weights, install Transformers, or claim model inference.
Run from the repository root:
    python -m unittest discover -s ai_engine/external_models -p 'test_*.py' -v
"""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import jais2_runtime as runtime


class Jais2AdapterContractTests(unittest.TestCase):
    def setUp(self):
        runtime._tokenizer = None
        runtime._model = None
        runtime._model_path = None

    def tearDown(self):
        runtime._tokenizer = None
        runtime._model = None
        runtime._model_path = None

    def test_missing_local_path_fails_closed(self):
        with patch.dict(os.environ, {"JON2_JAIS2_LOCAL_PATH": ""}):
            with self.assertRaisesRegex(RuntimeError, "rights-approved local checkpoint"):
                runtime._configured_path()

    def test_nonexistent_local_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = str(Path(temp_dir) / "not-a-model")
            with patch.dict(os.environ, {"JON2_JAIS2_LOCAL_PATH": missing}):
                with self.assertRaises(FileNotFoundError):
                    runtime._configured_path()

    def test_empty_message_is_rejected_before_loading(self):
        with patch.object(runtime, "load_runtime") as load:
            with self.assertRaises(ValueError):
                runtime.generate_reply("   ")
            load.assert_not_called()

    def test_generation_limit_is_validated_before_loading(self):
        with patch.object(runtime, "load_runtime") as load:
            with self.assertRaises(ValueError):
                runtime.generate_reply("اختبار", max_new_tokens=1025)
            load.assert_not_called()

    def test_loader_is_local_only_and_disables_remote_code(self):
        class FakeTokenizer:
            @classmethod
            def from_pretrained(cls, path, **kwargs):
                cls.call = (path, kwargs)
                return object()

        class FakeModel:
            @classmethod
            def from_pretrained(cls, path, **kwargs):
                cls.call = (path, kwargs)
                instance = cls()
                instance.evaluated = False
                return instance

            def eval(self):
                self.evaluated = True

        fake_transformers = types.SimpleNamespace(
            AutoTokenizer=FakeTokenizer,
            AutoModelForCausalLM=FakeModel,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(runtime, "_configured_path", return_value=Path(temp_dir)):
                with patch.dict(sys.modules, {"transformers": fake_transformers}):
                    runtime.load_runtime()

        self.assertTrue(runtime.model_is_ready())
        self.assertTrue(FakeTokenizer.call[1]["local_files_only"])
        self.assertFalse(FakeTokenizer.call[1]["trust_remote_code"])
        self.assertTrue(FakeModel.call[1]["local_files_only"])
        self.assertFalse(FakeModel.call[1]["trust_remote_code"])
        self.assertTrue(runtime._model.evaluated)


if __name__ == "__main__":
    unittest.main()
