import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from data_rights.corpus_builder import build_corpus


class CorpusBuilderTests(unittest.TestCase):
    def _manifest(self, root: Path, content: str):
        source = root / "source.txt"
        source.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest = {
            "schema_version": 1,
            "policy": {"wikipedia": "blocked", "cc_by_sa": "blocked"},
            "approved_sources": [{
                "dataset_id": "jon2/owner-written-seed",
                "version_or_commit": "a" * 40,
                "license": "custom-written-permission",
                "training_permission": True,
                "rights_evidence_url": "https://example.org/permission",
                "provenance_url": "https://example.org/provenance",
                "source_domains": ["owner-created.local"],
                "content_hash_sha256": digest,
                "human_approved": True,
                "local_path": "source.txt"
            }]
        }
        path = root / "approved_sources.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path, source

    def test_builds_deterministic_private_train_validation_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, _ = self._manifest(root, "\\n".join(f"جملة عربية رقم {i}" for i in range(100)))
            output = Path(tmp) / "private-output"
            report = build_corpus(manifest, root, output)
            self.assertEqual(report["documents"], 100)
            self.assertGreater(report["train_documents"], 0)
            self.assertGreater(report["validation_documents"], 0)
            self.assertTrue((output / "train.jsonl").is_file())
            self.assertTrue((output / "validation.jsonl").is_file())
            self.assertFalse(report["downloaded_data"])

    def test_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, source = self._manifest(root, "نص أصلي")
            source.write_text("نص تم تغييره", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                build_corpus(manifest, root, Path(tmp) / "private-output")

    def test_rejects_unapproved_source_and_empty_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, _ = self._manifest(root, "نص عربي")
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["approved_sources"][0]["human_approved"] = False
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Rights review failed"):
                build_corpus(manifest, root, Path(tmp) / "private-output")


if __name__ == "__main__":
    unittest.main()
