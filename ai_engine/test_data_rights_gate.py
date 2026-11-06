import json, tempfile, unittest
from pathlib import Path
from data_rights.rights_gate import load_approved_sources, validate_source

class RightsGateTests(unittest.TestCase):
    def valid(self):
        return {
            "dataset_id": "org/corpus",
            "version_or_commit": "a" * 40,
            "license": "cc0-1.0",
            "training_permission": True,
            "rights_evidence_url": "https://example.org/rights",
            "provenance_url": "https://example.org/provenance",
            "source_domains": ["example.org"],
            "content_hash_sha256": "b" * 64,
            "human_approved": True
        }
    def test_explicitly_approved_source_passes(self):
        self.assertEqual(validate_source(self.valid()), [])
    def test_sharealike_is_blocked(self):
        item = self.valid()
        item["license"] = "cc-by-sa-4.0"
        self.assertTrue(any("blocked" in e for e in validate_source(item)))
    def test_unknown_and_missing_training_permission_are_blocked(self):
        item = self.valid()
        item["license"] = "unknown"
        item["training_permission"] = False
        errors = validate_source(item)
        self.assertTrue(any("license" in e for e in errors))
        self.assertTrue(any("permission" in e for e in errors))
    def test_wikipedia_lineage_is_blocked(self):
        item = self.valid()
        item["source_domains"] = ["en.wikipedia.org"]
        self.assertTrue(any("Wikipedia" in e for e in validate_source(item)))
    def test_empty_manifest_is_valid_but_approves_no_data(self):
        manifest = {"schema_version": 1, "policy": {"wikipedia":"blocked","cc_by_sa":"blocked"}, "approved_sources":[]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(load_approved_sources(path), [])
    def test_policy_cannot_be_weakened(self):
        manifest = {"schema_version": 1, "policy": {"wikipedia":"allowed","cc_by_sa":"blocked"}, "approved_sources":[]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_approved_sources(path)

if __name__ == "__main__":
    unittest.main()
