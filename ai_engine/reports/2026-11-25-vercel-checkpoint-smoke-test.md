# Jon2 original checkpoint — Vercel Preview smoke test

Date: 2026-11-25  
Environment: Vercel Preview only  
Checkpoint: `jon2-last.pt`  
SHA-256: `edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2`  
Size: 3,471,600 bytes

## Runtime verification

- FastAPI liveness endpoint: HTTP 200.
- API health endpoint: HTTP 200.
- Private Blob retrieval completed successfully.
- Checkpoint SHA-256 verification passed.
- Original Jon2 checkpoint loaded on CPU.
- Runtime health reported `model_loaded=true`, `checkpoint_readable=true`, and `model_preload_state=loaded`.
- Public chat remained closed throughout the test.

## Actual generation results

Four fixed smoke-test cases were run against the loaded original checkpoint:

1. MSA explanation: generation completed, but the Arabic output was incoherent.
2. Egyptian instruction: generation completed, but the Arabic output was incoherent.
3. Basic arithmetic reasoning: generation completed, but the answer was incoherent.
4. Conversation context: generation was rejected by Jon2's text-integrity guard.

Representative outputs were malformed word fragments rather than useful answers. The technical model load succeeded; conversational quality did not.

## Release decision

**FAIL — do not open public chat.**

Keep all release flags false:

- `JON2_CHAT_RELEASE_APPROVED=false`
- `JON2_INFERENCE_TESTED=false`
- `JON2_QUALITY_REVIEW_PASSED=false`

The smoke test proves that the private checkpoint can be downloaded, hash-verified, loaded, and invoked on the Vercel CPU runtime. It does not prove language understanding, reasoning, reliable context retention, or production readiness.

Next work must focus on the original model's training data, model capacity, and held-out Arabic/Egyptian evaluation. Do not change release gates to bypass the failed quality result.
