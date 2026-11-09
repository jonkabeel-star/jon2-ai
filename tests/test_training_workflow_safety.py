import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "jon2-real-training.yml"


class TrainingWorkflowSafetyTests(unittest.TestCase):
    def test_legacy_training_is_manual_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        trigger_block = text.split("concurrency:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger_block)
        self.assertNotIn("schedule:", trigger_block)
        self.assertNotIn("\n  push:", trigger_block)
        self.assertIn(
            "inputs.confirm_legacy_training == 'RUN_LEGACY_269K_EXPERIMENT'",
            text,
        )

    def test_legacy_workflow_is_not_mislabeled_as_30m(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("not the arabic_30m profile", text)
        self.assertIn("legacy_original_transformer", text)

    def test_checkpoints_get_run_specific_names_and_sha256_manifest(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("jon2-legacy-" + "$" + "{" + "run_stamp}-best.pt", text)
        self.assertIn("jon2-legacy-" + "$" + "{" + "run_stamp}-resume.pt", text)
        self.assertIn("jon2-checkpoint-manifest-" + "$" + "{" + "stamp}.json", text)
        self.assertIn('"sha256": hashlib.sha256(raw).hexdigest()', text)
        self.assertIn("checkpoint-resume.sha256", text)

    def test_existing_checkpoint_evaluation_contract_is_preserved(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("training-output/checkpoint.sha256", text)
        self.assertIn("name: jon2-training-evidence", text)


if __name__ == "__main__":
    unittest.main()
