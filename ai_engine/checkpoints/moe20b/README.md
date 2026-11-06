# Jon2 MoE 20B checkpoints

This directory is reserved for the new 20B-class MoE training line only.

- Store private training checkpoints outside public Git history and never commit weight binaries.
- Use a distinct tokenizer and rights-approved corpus fingerprint.
- Record run configuration, step, token count, validation metrics, and SHA-256.
- Multi-rank FSDP checkpoint coordination is not implemented yet; do not save a multi-node run with the single-process checkpoint helper.
- No trained 20B checkpoint exists at this time.
