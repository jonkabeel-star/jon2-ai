"""Safety and deterministic unit tests for the quarantined Arabic corpus importer."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ai_engine import prepare_arabic_corpus as importer


ARABIC_SAMPLE = ("هذا نص عربي تجريبي يشرح موضوعاً معرفياً بصورة واضحة ومترابطة. " * 8).strip()


class ArabicCorpusImporterTests(unittest.TestCase):
    def test_clean_article_normalizes_unicode_and_whitespace(self):
        raw = "  " + ARABIC_SAMPLE.replace(" ", "  ") + "\x00  "
        cleaned = importer.clean_article(raw)
        self.assertEqual(cleaned, importer.clean_article(cleaned))
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("  ", cleaned)

    def test_clean_article_rejects_non_text_short_latin_and_urls(self):
        self.assertEqual(importer.clean_article(None), "")
        self.assertEqual(importer.clean_article("مرحبا"), "")
        self.assertEqual(importer.clean_article("A long English paragraph. " * 20), "")
        self.assertEqual(
            importer.clean_article(ARABIC_SAMPLE + " https://example.com"),
            "",
        )

    def test_destination_inside_approved_training_data_is_rejected(self):
        protected = Path(importer.__file__).resolve().parent / "training_data" / "unsafe"
        with self.assertRaisesRegex(ValueError, "inside ai_engine/training_data"):
            importer.ensure_quarantine_destination(protected)

    def test_prepare_refuses_nonempty_destination_before_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")
            fake_datasets = {"load_dataset": Mock()}
            with patch.dict("sys.modules", {"datasets": type("FakeDatasets", (), fake_datasets)()}):
                with self.assertRaises(FileExistsError):
                    importer.prepare(output, 200_000)
            fake_datasets["load_dataset"].assert_not_called()

    def test_prepare_writes_quarantined_manifest_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "quarantine"
            calls = []

            def fake_load_dataset(dataset_id, config, split, streaming):
                calls.append((dataset_id, config, split, streaming))
                return [
                    {"text": ARABIC_SAMPLE},
                    {"text": ARABIC_SAMPLE},  # exact duplicate
                    {"text": "English only " * 40},
                ]

            fake_module = type("FakeDatasets", (), {"load_dataset": staticmethod(fake_load_dataset)})
            with patch.dict("sys.modules", {"datasets": fake_module()}):
                manifest = importer.prepare(output, 200_000)

            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call[0] == importer.DATASET_ID for call in calls))
            self.assertTrue(all(call[2:] == ("train", True) for call in calls))
            self.assertEqual(manifest["approval_status"], "PENDING_HUMAN_LEGAL_AND_CONTENT_REVIEW")
            self.assertIs(manifest["training_allowed"], False)
            self.assertEqual(len(manifest["files"]), 2)
            for item in manifest["files"]:
                file_path = output / item["file"]
                self.assertEqual(item["article_count"], 1)
                self.assertEqual(item["sha256"], hashlib.sha256(file_path.read_bytes()).hexdigest())
                self.assertEqual(item["language_config"], next(
                    config for config in importer.DATASET_REVISION_CONFIGS
                    if config.endswith("." + item["file"].split("_")[1].split("_")[0])
                ))
            saved = json.loads((output / "source_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(saved["training_allowed"])
            self.assertEqual(saved["dataset_license"], "CC-BY-SA-4.0")


if __name__ == "__main__":
    unittest.main()
