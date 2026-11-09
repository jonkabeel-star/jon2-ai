"""Safety checks for the gated Arabic 30M workflow."""
from pathlib import Path
import unittest


WORKFLOW = Path(".github/workflows/jon2-arabic-30m.yml").read_text(encoding="utf-8")


class Arabic30MWorkflowSafetyTests(unittest.TestCase):
    def test_manual_dispatch_only_and_default_no_training(self):
        self.assertIn("workflow_dispatch:", WORKFLOW)
        self.assertNotIn("schedule:", WORKFLOW)
        self.assertNotIn("push:", WORKFLOW)
        self.assertIn("default: false", WORKFLOW)

    def test_preflight_must_succeed_before_training(self):
        self.assertIn("needs: preflight", WORKFLOW)
        self.assertIn("needs.preflight.result == 'success'", WORKFLOW)
        self.assertIn("needs.preflight.outputs.ready == 'true'", WORKFLOW)
        self.assertIn("inputs.approve_training == true", WORKFLOW)

    def test_training_requires_gpu_and_private_checkpoint_store(self):
        self.assertIn("[self-hosted, linux, x64, gpu]", WORKFLOW)
        self.assertIn("torch.cuda.is_available()", WORKFLOW)
        self.assertIn("KAGGLE_API_TOKEN", WORKFLOW)
        self.assertIn('private is not True', WORKFLOW)

    def test_uses_exact_30m_profile_and_preserves_unique_checkpoint_names(self):
        self.assertIn("--profile arabic_30m", WORKFLOW)
        self.assertIn("jon2-arabic-30m-${GITHUB_RUN_ID}-best.pt", WORKFLOW)
        self.assertIn("jon2-arabic-30m-${GITHUB_RUN_ID}-resume.pt", WORKFLOW)
        self.assertIn('"sha256"', WORKFLOW)

    def test_weights_are_not_uploaded_as_public_github_artifact(self):
        self.assertIn("Save immutable run-specific checkpoints to private Kaggle version", WORKFLOW)
        self.assertIn("Upload non-sensitive training evidence only", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
