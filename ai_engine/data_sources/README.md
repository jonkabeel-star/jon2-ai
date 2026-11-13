# Arabic dataset intake

See `arabic_dataset_registry.json` for candidate sources and their review status.

**Nothing in the registry is approved for training.** A repository-level license badge is not proof that every underlying source is licensed for model training. Before importing any candidate:

1. Review its full dataset card, exact license text, terms of access, and source-level provenance.
2. Confirm that rights cover machine-learning training and the intended distribution/commercial use of Jon2.
3. Check privacy, personal data, copyrighted extracts, quality, domain balance, and duplication.
4. Download only into a private quarantine location; compute SHA-256 and exact record/token counts.
5. Split by source/document before training to avoid leakage. Keep evaluation data separate.
6. Obtain explicit owner approval for each exact file and add its hash and rights basis to the private `source_approvals.json` manifest.

## Candidate summary

- ArabicText-Large: large MSA candidate; declared Apache-2.0; quarantined pending source provenance.
- DIA2: MSA candidate; declared Apache-2.0; access condition and source provenance require review; very large download.
- ArSyra: useful dialect/instruction candidate, but preview declares CC-BY-NC-SA-4.0; not approved for commercial training.
- BAREC-10M: readability corpus, declared CC-BY-SA-4.0; assess share-alike and source rights.
- 3arabLM-corpus: pre-tokenized, Shamela-derived specialized candidate; tokenizer and source rights require review.

No external corpus was downloaded or added to Git. No private user data or model weights were added.
