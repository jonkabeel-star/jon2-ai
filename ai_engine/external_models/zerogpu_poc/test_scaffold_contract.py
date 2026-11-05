"""Offline contract tests for the locked ZeroGPU scaffold.

These tests parse source only: they never import Gradio/Spaces/Transformers,
download weights, request GPU time, or contact Hugging Face.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


APP = Path(__file__).with_name("app.py")


class ZeroGPUScaffoldContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_all_four_explicit_gates_are_required(self):
        for expression in (
            'os.getenv("JON2_MODEL_RIGHTS_APPROVED", "").strip() == "YES"',
            'os.getenv("JON2_HF_ACCESS_ACCEPTED", "").strip() == "YES"',
            'bool(re.fullmatch(r"[0-9a-fA-F]{40}", REVISION))',
            'bool(HF_TOKEN)',
        ):
            self.assertIn(expression, self.source)
        self.assertIn(
            "MODEL_ENABLED = RIGHTS_APPROVED and HF_TERMS_ACCEPTED and REVISION_VALID and bool(HF_TOKEN)",
            self.source,
        )

    def test_enabled_handler_is_wrapped_with_zerogpu(self):
        functions = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        handler = functions["reply_enabled"]
        self.assertTrue(handler.decorator_list)
        decorator = handler.decorator_list[0]
        self.assertIsInstance(decorator, ast.Call)
        self.assertEqual(ast.unparse(decorator.func), "spaces.GPU")
        duration = {item.arg: item.value for item in decorator.keywords}.get("duration")
        self.assertEqual(ast.unparse(duration), "45")

    def test_gradio_events_use_the_selected_handler(self):
        self.assertIn("handler = reply_enabled if MODEL_ENABLED else reply_locked", self.source)
        self.assertIn("send.click(fn=handler, inputs=message, outputs=answer)", self.source)
        self.assertIn("message.submit(fn=handler, inputs=message, outputs=answer)", self.source)

    def test_locked_handler_never_runs_inference(self):
        functions = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        locked = ast.unparse(functions["reply_locked"])
        self.assertIn("raise gr.Error(status_text())", locked)
        self.assertNotIn("model.generate", locked)
        self.assertNotIn("torch", locked)


    def test_model_download_and_loading_are_inside_owner_gate(self):
        top_level_loads = [
            node for node in self.tree.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "from_pretrained"
        ]
        self.assertEqual(top_level_loads, [])
        gated_blocks = [
            node for node in self.tree.body
            if isinstance(node, ast.If) and ast.unparse(node.test) == "MODEL_ENABLED"
        ]
        self.assertEqual(len(gated_blocks), 2)
        gated_source = "\\n".join(ast.unparse(node) for node in gated_blocks)
        self.assertIn("AutoTokenizer.from_pretrained", gated_source)
        self.assertIn("AutoModelForCausalLM.from_pretrained", gated_source)

    def test_secrets_are_not_rendered_or_logged(self):
        self.assertNotIn("HF_TOKEN}", self.source)
        self.assertNotIn("print(HF_TOKEN", self.source)
        self.assertIn("load_error = type(exc).__name__", self.source)

    def test_model_loading_disables_remote_code_and_uses_fixed_revision(self):
        self.assertIn("revision=REVISION", self.source)
        self.assertIn("trust_remote_code=False", self.source)
        self.assertNotIn("trust_remote_code=True", self.source)
        self.assertNotIn("local_files_only=True", self.source)  # Space downloads only after owner approval gates.


if __name__ == "__main__":
    unittest.main()
