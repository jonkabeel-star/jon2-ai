# Jon2 AI local-only audit — 2026-11-13

## Scope and safety

This is a source-code audit only. It does not load, modify, move, publish, or delete private model weights or private training data. It does not change the public release gate. No external AI provider or model download was used for this audit.

## Verified repository findings

1. The project contains an original from-scratch PyTorch Transformer in `ai_engine/jon2_core.py`. Its docstring explicitly says weights start random and it does not load a pretrained model or hosted AI API.
2. The FastAPI runtime in `ai_engine/chat_engine.py` loads the original Jon2 checkpoint through `jon2_core.load_model`; it does not use the separate Qwen wrapper.
3. `ai_engine/language_engine.py` is a separate legacy path that defaults to `Qwen/Qwen2.5-0.5B-Instruct` and calls Hugging Face `from_pretrained`. That path requires an external model download and must not be used for the independent Jon2 runtime.
4. A browser-side inference implementation already exists under `pocket/`: `jon2-transformer.js`, `jon2-tokenizer.js`, `jon2-safari-bundle.js`, `jon2-inference-worker.js`, and `jon2-safari-client.js`. The Safari loader verifies checkpoint and weights SHA-256 values and runs inference in a local Web Worker.
5. The browser runtime requires a compatible private bundle (manifest plus binary weights). The source repository does not itself establish that the private checkpoint is available to the browser or prove that the bundle can be created on the iPhone.
6. `jon2-config.js` currently sets `JON2_API_BASE_URL` to `https://jon2-ai.pages.dev`. This is an external server origin and conflicts with a strict device-only/offline direction.
7. `ai_engine/main.py` contains external-host service routes and optional checkpoint preloading. These are server capabilities, not a way to execute Python/PyTorch directly inside Safari.
8. `docs/SAFARI_LOCAL_MODEL_AR.md` still documents a Kaggle export workflow. That workflow conflicts with the new no-external-websites requirement and must be replaced before presenting the local path as self-contained.
9. The human review and public release gate is intentionally blocked. Existing documentation reports the historical 269,952-parameter checkpoint's Arabic outputs as incoherent and says no human release approval exists. This gate must remain closed.

## Required next implementation sequence

1. Trace the exact Python-to-Safari checkpoint export format and verify tensor parity against the current original checkpoint metadata without accessing or copying private weights.
2. Remove the Qwen/Hugging Face legacy wrapper from the default Jon2 execution path; retain it only if there is a separately justified, clearly disabled research-only use.
3. Make the browser application default to local-only mode and remove implicit calls to the Pages/Render API. Keep an explicit offline/local status and do not show canned small-talk responses as evidence that the Transformer is loaded.
4. Replace the Kaggle-based Safari instructions with a local export/import workflow that does not depend on third-party AI/model hosting. Do not claim this is possible on iPhone alone until the checkpoint conversion can actually run there or the user has a local copy of the approved checkpoint bundle.
5. Add/extend tests that prove no network request is made for chat inference, the local worker requires verified model weights, and missing weights produce a clear unavailable state.
6. Run the repository's Python and JavaScript checks. Report any missing private artifacts or hardware requirements rather than bypassing checks.
7. Keep all weights, private corpora, source approvals, and release attestations unchanged. Do not merge or publish a model without the required human review.

## Important hardware limitation

A browser can run the existing small JavaScript inference engine locally, but it cannot directly execute the Python/PyTorch runtime. Training a useful Transformer from scratch on an iPhone 12 Pro Max is not a realistic path. A genuinely independent, offline deployment needs a compatible checkpoint file already owned by the project and enough device memory to load it. Software can be free; substantial model training still requires compute resources.

## Audit outcome

The project has a real original Transformer code path and an experimental Safari JavaScript inference path, but it is not yet a complete, verified, self-contained offline assistant. No model-ready or conversational-quality claim is made by this audit.
