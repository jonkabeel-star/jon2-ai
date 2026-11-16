import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_DIR = ROOT / "kaggle" / "hello-jon2"
NOTEBOOK = KERNEL_DIR / "hello-jon2.ipynb"
METADATA = KERNEL_DIR / "kernel-metadata.json"
WORKFLOW = ROOT / ".github" / "workflows" / "kaggle-bridge.yml"
TRAINER = ROOT / "ai_engine" / "train_jon2.py"


class KaggleGpuTrainingSafetyTests(unittest.TestCase):
    def test_kernel_is_private_gpu_and_uses_private_approved_dataset(self):
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        self.assertTrue(metadata["is_private"])
        self.assertTrue(metadata["enable_gpu"])
        self.assertIn("jon2kabeel/jon2-approved-training-data-v2", metadata["dataset_sources"])

    def test_notebook_requires_gpu_and_current_training_gates(self):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        source = "\\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell["cell_type"] == "code"
        )
        self.assertIn("torch.cuda.is_available()", source)
        self.assertIn("--require-cuda", source)
        self.assertIn("--minimum-characters", source)
        self.assertIn("1000000", source)
        self.assertIn("--minimum-tokens-per-parameter", source)
        self.assertIn("20", source)
        self.assertIn("preflight_training.py", source)
        self.assertIn("No weights were created or changed", source)

    def test_github_bridge_preflights_before_pushing_gpu_kernel(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("preflight_training.py", workflow)
        self.assertIn("--minimum-characters 1000000", workflow)
        self.assertIn("--minimum-tokens-per-parameter 20", workflow)
        self.assertLess(
            workflow.index("preflight_training.py"),
            workflow.index("kaggle kernels push"),
        )
        self.assertIn("No Kaggle GPU job was started", workflow)

    def test_trainer_has_explicit_cuda_fail_closed_option(self):
        trainer = TRAINER.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--require-cuda"', trainer)
        self.assertIn("No CPU fallback was started", trainer)


if __name__ == "__main__":
    unittest.main()
