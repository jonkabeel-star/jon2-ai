import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from data_rights.corpus_builder import build_corpus


class CorpusBuilderTests(unittest.TestCase):
    def _manifest(self, root: Path):
        sources = []
        for dataset_id, filename, split, count in (
            ("jon2/owner-written-train", "train.txt", "train", 100),
            ("jon2/owner-written-validation", "validation.txt", "validation", 30),
        ):
            source = root / filename
            source.write_text("\n".join(f"جملة عربية {split} رقم {i}" for i in range(count)), encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            sources.append({
                "dataset_id": dataset_id,
                "version_or_commit": "a" * 40,
                "license": "custom-written-permission",
                "training_permission": True,
                "rights_evidence_url": "https://example.org/permission",
                "provenance_url": "https://example.org/provenance",
                "source_domains": ["owner-created.local"],
                "content_hash_sha256": digest,
                "human_approved": True,
                "local_path": filename,
                "split": split,
            })
        manifest = {
            "schema_version": 1,
            "policy": {"wikipedia": "blocked", "cc_by_sa": "blocked"},
            "approved_sources": sources,
        }
        path = root / "approved_sources.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path, root / "train.txt"

    def test_builds_source_disjoint_private_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, _ = self._manifest(root)
            output = Path(tmp) / "private-output"
            report = build_corpus(manifest, root, output)

            self.assertEqual(report["documents"], 130)
            self.assertEqual(report["train_documents"], 100)
            self.assertEqual(report["validation_documents"], 30)
            self.assertTrue((output / "train.jsonl").is_file())
            self.assertTrue((output / "validation.jsonl").is_file())
            self.assertFalse(report["downloaded_data"])

            train_lines = (output / "train.jsonl").read_text(encoding="utf-8").splitlines()
            validation_lines = (output / "validation.jsonl").read_text(encoding="utf-8").splitlines()
            train_records = [json.loads(line) for line in train_lines]
            validation_records = [json.loads(line) for line in validation_lines]
            self.assertEqual(len(train_records), 100)
            self.assertEqual(len(validation_records), 30)
            self.assertTrue((output / "train.jsonl").read_bytes().endswith(b"\n"))
            self.assertTrue((output / "validation.jsonl").read_bytes().endswith(b"\n"))
            self.assertTrue(
                {record["text"] for record in train_records}.isdisjoint(
                    record["text"] for record in validation_records
                )
            )

    def test_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, source = self._manifest(root)
            source.write_text("نص تم تغييره", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                build_corpus(manifest, root, Path(tmp) / "private-output")

    def test_rejects_unapproved_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest, _ = self._manifest(root)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["approved_sources"][0]["human_approved"] = False
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Rights review failed"):
                build_corpus(manifest, root, Path(tmp) / "private-output")

    def test_rejects_output_inside_repository_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            data_root = temp_root / "private-data"
            data_root.mkdir()
            manifest, _ = self._manifest(data_root)

            repository = temp_root / "repository"
            (repository / ".git").mkdir(parents=True)
            manifest_in_repo = repository / "ai_engine" / "data_rights" / "approved_sources.json"
            manifest_in_repo.parent.mkdir(parents=True)
            manifest_in_repo.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
            output = repository / "generated-corpus"

            with self.assertRaisesRegex(ValueError, "inside the Git repository"):
                build_corpus(manifest_in_repo, data_root, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
