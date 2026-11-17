"""Tests for the fail-closed Open Arabic Books rights-screening utility."""
import json
import tempfile
import unittest
from pathlib import Path

from screen_open_arabic_books_rights import read_metadata, screen_record, screen_rows


def sample_record(**overrides):
    record = {
        "book_id": "hindawi-12345678",
        "title": "كتاب تجريبي",
        "is_translation": False,
        "design_license": "CC-BY-4.0",
        "translation_covered": False,
        "original_text_status": "public-domain",
        "license_decision": "text_public_domain",
        "license_quote": "نص الترخيص التجريبي",
        "license_checked_at": "2026-11-04",
        "rights_statement": "بيان الحقوق كما ورد في بيانات المصدر",
        "attribution": "سطر النسبة الكامل",
        "book_url": "https://www.hindawi.org/books/12345678/",
        "source_file_sha256": "a" * 64,
        "upstream_dataset": "https://doi.org/10.5878/7rbh-gy93",
        "credits": [{"role": "author", "name": "مؤلف تجريبي", "death_year": 1940}],
    }
    record.update(overrides)
    return record


class OpenArabicBooksRightsTests(unittest.TestCase):
    def test_valid_non_translation_is_review_only_never_approved(self):
        result = screen_record(sample_record())
        self.assertEqual(result["screening_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(result["training_approval"], "NOT_GRANTED")
        self.assertIn(
            "publisher_public_domain_statement_is_not_an_egyptian_legal_determination",
            result["human_review_reasons"],
        )

    def test_valid_translation_requires_explicit_translation_coverage(self):
        record = sample_record(
            is_translation=True,
            translation_covered=True,
            original_text_status="public-domain",
            license_decision="translation_cc_by_4_original_public_domain",
        )
        result = screen_record(record)
        self.assertEqual(result["screening_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(result["blockers"], [])

    def test_translation_without_coverage_is_held(self):
        record = sample_record(
            is_translation=True,
            translation_covered=False,
            license_decision="translation_cc_by_4_original_public_domain",
        )
        result = screen_record(record)
        self.assertEqual(result["screening_status"], "HOLD")
        self.assertIn("arabic_translation_not_explicitly_covered", result["blockers"])

    def test_design_license_must_be_exact_cc_by_4(self):
        result = screen_record(sample_record(design_license="CC-BY-NC-4.0"))
        self.assertEqual(result["screening_status"], "HOLD")
        self.assertIn("design_license_not_exact_cc_by_4_0", result["blockers"])

    def test_source_hash_is_mandatory(self):
        result = screen_record(sample_record(source_file_sha256="not-a-hash"))
        self.assertEqual(result["screening_status"], "HOLD")
        self.assertIn("invalid_source_file_sha256", result["blockers"])

    def test_unexpected_license_decision_is_held(self):
        result = screen_record(sample_record(license_decision="held_for_reading"))
        self.assertEqual(result["screening_status"], "HOLD")
        self.assertIn("license_decision_does_not_match_book_rights_fields", result["blockers"])

    def test_missing_author_death_year_is_flagged_for_review(self):
        record = sample_record(credits=[{"role": "author", "name": "مؤلف بلا تاريخ"}])
        result = screen_record(record)
        self.assertEqual(result["screening_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn(
            "author_death_year_missing_requires_egyptian_rights_review",
            result["human_review_reasons"],
        )

    def test_late_author_death_year_is_flagged_for_egyptian_review(self):
        record = sample_record(credits=[{"role": "author", "name": "مؤلف حديث", "death_year": 1990}])
        result = screen_record(record)
        self.assertIn(
            "author_death_year_after_1976_requires_egyptian_rights_review",
            result["human_review_reasons"],
        )

    def test_cc_by_3_original_text_is_reviewed_separately(self):
        record = sample_record(
            is_translation=True,
            translation_covered=True,
            original_text_status="CC-BY-3.0",
            license_decision="translation_cc_by_4_original_cc_by",
        )
        result = screen_record(record)
        self.assertEqual(result["screening_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn(
            "original_text_uses_cc_by_3_0_terms_requiring_separate_review",
            result["human_review_reasons"],
        )

    def test_duplicate_book_ids_are_held(self):
        results = screen_rows([sample_record(), sample_record()])
        self.assertEqual(results[0]["screening_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(results[1]["screening_status"], "HOLD")
        self.assertIn("duplicate_book_id", results[1]["blockers"])

    def test_reads_jsonl_metadata_without_book_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.jsonl"
            path.write_text(json.dumps(sample_record(), ensure_ascii=False) + "\n", encoding="utf-8")
            rows = read_metadata(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["book_id"], "hindawi-12345678")

    def test_parquet_or_text_inputs_are_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.parquet"
            path.write_bytes(b"not parsed")
            with self.assertRaises(ValueError):
                read_metadata(path)


if __name__ == "__main__":
    unittest.main()
