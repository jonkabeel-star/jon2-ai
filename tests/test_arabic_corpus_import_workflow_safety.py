"""Safety contract for the manual-only Arabic corpus import workflow."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "jon2-arabic-corpus-import.yml").read_text(encoding="utf-8")


class ArabicCorpusImportWorkflowSafetyTests(unittest.TestCase):
    def test_manual_dispatch_only_with_bounded_default(self):
        trigger = WORKFLOW.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("schedule:", trigger)
        self.assertNotIn(chr(10) + "  push:", trigger)
        self.assertIn('default: "10000000"', trigger)
        normalized_workflow = "".join(WORKFLOW.split()).replace("_", "")
        self.assertIn("not200000<=int(value)<=10000000:", normalized_workflow)

    def test_import_is_quarantine_only_and_never_trains(self):
        self.assertIn("/tmp/jon2-arabic-quarantine", WORKFLOW)
        self.assertIn("prepare_arabic_corpus.py", WORKFLOW)
        self.assertIn("audit_corpus_quality.py", WORKFLOW)
        self.assertNotIn("train_jon2.py", WORKFLOW)
        self.assertNotIn("source_approvals.json", WORKFLOW)
        self.assertNotIn("checkpoints/", WORKFLOW)
        self.assertIn('"training_allowed": False', WORKFLOW)

    def test_public_artifact_contains_metadata_not_raw_corpus(self):
        self.assertIn("metadata-only", WORKFLOW)
        self.assertIn('"sample_source_links"', WORKFLOW)
        self.assertNotIn("path: /tmp/jon2-arabic-quarantine", WORKFLOW)
        self.assertIn("retention-days: 14", WORKFLOW)

    def test_no_private_credentials_or_checkpoint_secrets_required(self):
        self.assertNotIn("KAGGLE_API_TOKEN", WORKFLOW)
        self.assertNotIn("HF_TOKEN", WORKFLOW)
        self.assertIn("permissions:" + chr(10) + "  contents: read", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
