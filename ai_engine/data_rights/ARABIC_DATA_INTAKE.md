# Jon2 Arabic data intake and expansion plan

## Purpose

This workflow helps the owner grow a high-quality Arabic corpus without weakening the existing source-rights gate. It is an intake and review process, not an automatic data-acquisition or training system.

## Allowed intake lanes

1. **Owner-written material**: original dialogue, explanations, stories, instructions, and Egyptian Arabic/MSA examples written for Jon2. Keep dated authorship records and a source-specific SHA-256.
2. **Commissioned material**: text created under a written agreement that explicitly grants the intended model-training rights, including commercial use if that is a future goal.
3. **Public-domain material**: only when the exact underlying work and edition are verified as public domain in the relevant jurisdictions. A modern transcription, translation, annotation, or edition may have separate rights.
4. **Third-party datasets**: only after source-level provenance, exact version, underlying-text rights, explicit ML training permission, privacy review, and human approval are documented. The existing strict rights allowlist remains authoritative.

Do not treat a dataset as safe merely because it is publicly downloadable, called open-source, or carries a software licence. Do not scrape websites or harvest private conversations. Keep held-out evaluation material separate from training.

## Candidate intake

Run the read-only local audit:

~~~bash
python -m ai_engine.data_rights.intake_audit --candidate /secure/candidates/arabic_batch_001.txt --output /secure/reports/arabic_batch_001.json
~~~

The report records the candidate's byte hash, character/document counts, Arabic-script signals, normalized exact duplicates, and privacy/integrity signal counts. It does not print matched email/phone values. It does not decide rights or semantic quality and always reports `training_eligible=false`.

Then complete `ai_engine/training_data/SOURCE_MANIFEST_TEMPLATE.md`, verify the exact source bytes and rights evidence, and ask a human reviewer to make the approval decision. Only after the separate approval manifest binds approval to the exact SHA-256 and character count can an approved source be considered for the existing corpus builder.

## Quality review before approval

- Check Arabic MSA and Egyptian dialect coverage separately; Arabic-script percentage is not a dialect classifier.
- Review factuality, clarity, instruction following, natural dialogue, spelling, punctuation, and repeated boilerplate manually.
- Remove personal data, credentials, private messages, phone numbers, and email addresses unless there is a documented lawful basis and a clear need.
- Check exact and near duplicates, benchmark/evaluation contamination, and source-level train/validation leakage.
- Keep a human-reviewed sample from every source and record known limitations.
- Keep candidate data, rights evidence, and final corpora out of the public Git repository unless the content itself is approved for public release.

## Scale responsibly

The current `arabic_30m` preflight applies a 10-token-per-parameter planning threshold. For a 30-million-parameter model, that is roughly 300 million training tokens. This is a project-specific conservative gate, not a universal law of model training. Do not meet it by repeating or synthetically duplicating the same small corpus. Expand in measured, source-diverse batches and rerun the tokenizer, quality, privacy, rights, and held-out evaluation audits after each batch.

A useful next milestone is a manually reviewed pilot batch with balanced MSA and Egyptian Arabic, several content domains, no personal data, and fully documented ownership/permission. The pilot is for pipeline validation only; it is not a training authorization.

## Safety boundaries

- No network downloads or scraping in the intake audit.
- No changes to the current approved training files.
- No automatic rights approval.
- No model training, checkpoint creation, deployment, or public-chat release.
- Existing approval manifests and checkpoints remain unchanged unless the owner explicitly authorizes a separate reviewed change.
