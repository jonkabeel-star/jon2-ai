# Jon2 Arabic external model adapters

## Current selection

The owner selected an 8B model target with Egyptian Arabic as the first language priority and MSA as a core capability. Jais 2 8B Chat is the exact-size candidate currently prepared for evaluation.

## Important status

- Jais 2's model repository declares Apache-2.0 for the model release.
- The public model card does not provide the detailed source-level training-data provenance and rights evidence required by Jon2's policy.
- Hugging Face currently requires an authenticated user to review and accept access conditions before downloading the model files.
- Therefore the checkpoint is **not approved for download or deployment yet**.
- Do not treat the repository's model license as proof that every underlying training text is cleared.
- Do not use the adapter until the owner completes the rights review and accepts the model access terms.

See [JON2_ARABIC_8B_AUDIT.md](JON2_ARABIC_8B_AUDIT.md).

## Local-only runtime adapter

`jais2_runtime.py` is preparation code. It:
- Loads only from a local directory configured with `JON2_JAIS2_LOCAL_PATH`.
- Uses `local_files_only=True`; it will not download model files.
- Sets `trust_remote_code=False`.
- Uses the model's chat template and a Jon2 Egyptian-first system instruction.
- Does not call any hosted inference provider.
- Is not connected to the public API route and is not release-approved.

## Resource note

The model card identifies 8B BF16 weights. The raw parameter storage alone is approximately 16 GB, before memory for the runtime, KV cache, and operating system. A real inference host needs additional RAM/VRAM. An iPhone cannot host this model. Do not assume a free notebook session is a permanent web server.

## Safe activation sequence

1. Complete written training-data provenance and rights review.
2. Owner reviews and accepts Hugging Face access conditions.
3. Download the exact reviewed model revision to private storage outside the public Git repository.
4. Record the exact revision, file hashes, license, and rights decision in a private deployment manifest.
5. Install a Transformers version/fork that supports Jais2 and validate the model in an isolated test environment.
6. Run held-out Egyptian Arabic, MSA, multi-turn, factuality, and safety evaluations.
7. Human-review the full report.
8. Only then consider connecting the adapter to a private Jon2 API route. Keep the original Jon2 model path separate.
