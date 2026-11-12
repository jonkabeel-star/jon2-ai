"""Safety tests for the quarantined Arabic Wikipedia collector."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_engine.collect_wikipedia_ar import (
    DEFAULT_OUTPUT_DIR,
    QUARANTINE_STATUS,
    _assert_quarantine_destination,
    collect_corpus,
)


class QuarantinedCollectorTests(unittest.TestCase):
    def test_default_destination_is_outside_training_data(self):
        self.assertEqual(DEFAULT_OUTPUT_DIR, "private-corpus-quarantine/wikipedia_ar")

    def test_training_data_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            _assert_quarantine_destination(Path("ai_engine/training_data/private-wikipedia"))

    def test_collection_is_quarantined_and_never_approves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "private-quarantine"
            article = "هذا نص عربي تجريبي مفيد. " * 5000
            payload = {
                "query": {
                    "pages": [{
                        "pageid": 123,
                        "title": "مقالة تجريبية",
                        "fullurl": "https://ar.wikipedia.org/wiki/test",
                        "extract": article,
                        "revisions": [{
                            "revid": 987,
                            "timestamp": "2026-11-12T00:00:00Z",
                        }],
                    }]
                }
            }
            with patch("ai_engine.collect_wikipedia_ar.fetch_batch", return_value=payload):
                chars, count = collect_corpus(output, target_chars=100_000, max_pages=1)

            self.assertGreaterEqual(chars, 100_000)
            self.assertEqual(count, 1)
            self.assertTrue((output / "wikipedia_ar_QUARANTINED_NOT_FOR_TRAINING.txt").is_file())
            manifest = json.loads(
                (output / "wikipedia_ar_quarantine_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], QUARANTINE_STATUS)
            self.assertFalse(manifest["training_eligible"])
            self.assertFalse(manifest["commercial_use_eligible"])
            self.assertFalse(manifest["approval_created"])
            self.assertFalse(manifest["approval_manifest_modified"])
            record = manifest["articles"][0]
            self.assertEqual(record["revision_id"], 987)
            self.assertEqual(record["status"], QUARANTINE_STATUS)
            self.assertFalse(record["training_eligible"])
            self.assertFalse(record["commercial_use_eligible"])
            self.assertFalse((output / "source_approvals.json").exists())


if __name__ == "__main__":
    unittest.main()
