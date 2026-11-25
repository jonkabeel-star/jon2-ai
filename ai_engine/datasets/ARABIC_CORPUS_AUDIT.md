# Read-only Arabic corpus audit

The file ai_engine/audit_arabic_corpus.py is a dependency-free, offline diagnostic for existing train/validation/test JSONL partitions.

## What it checks

- UTF-8 and JSONL structure.
- Text records have a non-empty text field.
- Dialogue records start with a user turn, end with an assistant turn, and alternate roles.
- Empty partitions and exact duplicate normalized text within and across splits.
- Repeated conversation_id, document_id, or group_id across splits.
- Possible email/phone patterns and records without Arabic script.
- Aggregate Arabic/Latin script counts. It explicitly does not infer Egyptian vs MSA.

## Example (private files only)

    python ai_engine/audit_arabic_corpus.py \
      --mode text \
      --train /private/jon2/splits/train.jsonl \
      --validation /private/jon2/splits/validation.jsonl \
      --test /private/jon2/splits/test.jsonl \
      --output /private/jon2/reports/corpus-audit.json

For structured conversation records, use --mode dialogue.

Exit code 2 means diagnostic blockers were found. A clean report still sets ready_for_training=false and all human approvals to false. It is not a licence check, privacy clearance, dialect-quality score, or semantic evaluation. Reports contain hashes/counts/flags, never raw record text. The command does not mutate inputs, download data, approve sources, or train.

Run tests with:

    python -m unittest ai_engine.tests.test_research_corpus_audit -v
