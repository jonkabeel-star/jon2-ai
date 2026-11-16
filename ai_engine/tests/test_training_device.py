import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai_engine"))

from train_jon2 import resolve_training_device


class TrainingDeviceGateTests(unittest.TestCase):
    def test_cpu_is_allowed_for_non_gpu_runs(self):
        self.assertEqual(resolve_training_device(False, cuda_available=False).type, "cpu")

    def test_required_cuda_fails_closed_when_gpu_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "No CPU fallback was started"):
            resolve_training_device(True, cuda_available=False)

    def test_required_cuda_selects_cuda_when_available(self):
        self.assertEqual(resolve_training_device(True, cuda_available=True).type, "cuda")


if __name__ == "__main__":
    unittest.main()
