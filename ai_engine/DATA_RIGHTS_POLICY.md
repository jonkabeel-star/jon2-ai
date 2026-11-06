# Jon2 Arabic data rights gate

The initial manifest intentionally approves **zero third-party datasets**.

A source is eligible only after a human verifies the exact version, the underlying source domains, provenance, a source-specific rights statement, and explicit permission for model training. A public download link or an "open" label is not enough.

Jon2 policy blocks:
- Wikipedia/Wikimedia-derived material.
- CC BY-SA and other share-alike terms.
- Missing, unknown, or ambiguous licenses.
- Datasets whose card license does not cover the underlying source material.
- Sources without a pinned version/commit and SHA-256 fingerprint.
- Sources without human approval.

The gate currently accepts only CC0 1.0, public-domain material with evidence, or a custom written grant that explicitly permits model training. Software licenses such as MIT/Apache are not treated as automatic data-training permission.

## Separation from the original Jon2 model

The original small Jon2 checkpoint and its approved seed corpus are not included in this new 20B data manifest. They remain a separate research line. New MoE training must use its own tokenizer, corpus manifest, checkpoint directory, and run metadata. Never overwrite the original checkpoint path.

## Current status

No external corpus is approved. No third-party dataset has been downloaded. No training run has started.
