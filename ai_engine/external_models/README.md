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


## Egyptian Arabic evaluation suite

The owner-authored evaluation assets are in `evaluation/`:

- `jon2_arabic_eval_v1.json`: 16 short conversations covering Egyptian dialect, MSA, multi-turn coherence, factual uncertainty, instruction following, privacy, honesty, and prompt injection.
- `run_evaluation.py`: local-only runner that uses the configured checkpoint through `jais2_runtime.py` and writes a JSON report to the local filesystem.
- Validate the suite without model weights:
  `python ai_engine/external_models/evaluation/run_evaluation.py --validate-only`
- Run inference only after rights approval and local checkpoint setup:
  `JON2_JAIS2_LOCAL_PATH=/private/path/to/approved/model python ai_engine/external_models/evaluation/run_evaluation.py`

The suite contains project-authored prompts, not scraped benchmark material. The runner does not call a hosted inference API. It does not assign an automatic quality score: a human must review every output. Do not commit generated reports if they contain private prompts or other sensitive data. The evaluation runner is not evidence that a checkpoint has been downloaded or tested.


## Private Jon2 Arabic API (disabled by default)

The FastAPI router is mounted separately from the original Jon2 chat engine:

- `POST /api/jais2/chat`
- `GET /api/jais2/health`

The API is **disabled unless** `JON2_JAIS2_API_ENABLED=true`. Chat also requires a secret `JON2_JAIS2_API_TOKEN` and an HTTP header `Authorization: Bearer <token>`. Never put this token in GitHub, the browser, or the static GitHub Pages frontend. Use a private server-side client over HTTPS only.

Required server-side environment values after rights approval and private checkpoint installation:

- `JON2_JAIS2_API_ENABLED=true`
- `JON2_JAIS2_API_TOKEN` = a long random secret
- `JON2_JAIS2_LOCAL_PATH` = path to the approved local checkpoint

With the default configuration, the new health endpoint reports `disabled` and chat returns HTTP 503. Importing the route does not import Transformers or load weights. The original `/api/chat` behavior and its release gate remain separate.

## Dependency version policy (reviewed 2026-11-05)

- FastAPI 0.162.0 is the current PyPI release checked for the route test environment.
- Transformers 5.22.1 is the current PyPI release checked. Upstream Transformers documentation includes Jais2 support, but the Jais 2 model card also documents a Jais-2-compatible Transformers fork. Do not assume the PyPI wheel and publisher's fork are interchangeable until the exact checkpoint is smoke-tested.
- PyTorch 2.15.0 is the current PyPI release checked. Do not force-upgrade the production host blindly: choose the wheel matching its Python, CPU/CUDA, and driver environment.

These are version checks, not a claim that the model has been loaded or tested. The model remains blocked pending training-data rights clarification and an owner-approved checkpoint.
