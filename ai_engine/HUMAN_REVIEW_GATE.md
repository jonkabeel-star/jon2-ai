# Jon2 AI — Human Review and Public Chat Release Gate

**Status: BLOCKED — no human approval has been recorded for the current checkpoint.**

## What automation has and has not established

- CI can check imports, syntax, API contracts, data approval fingerprints, checkpoint file integrity, and container buildability.
- A model loading successfully or generating text on CPU is only an execution smoke test.
- Automatic metrics such as answer length, Arabic-character ratio, and repetition do not establish meaning, factual accuracy, coherence, safety, or Egyptian dialect quality.
- The historical 269,952-parameter checkpoint completed 1,200 optimizer steps, but its 40-prompt held-out outputs were reported as visibly malformed/incoherent Arabic. It is not eligible for public chat.
- The new Egyptian draft has 80 dialogue turns and a separate 30-prompt evaluation set. Neither constitutes human approval.

## Human review record required for each candidate checkpoint

A reviewer must record all of the following against one immutable candidate:

- checkpoint version/name and SHA-256;
- training run ID, commit SHA, training configuration, tokenizer SHA-256, and corpus SHA-256;
- evaluation artifact/run ID and exact evaluation prompt-set version;
- reviewer identity and review date;
- a score and written note for every prompt/answer pair;
- defects, including invented facts/names, dialect errors, context loss, arithmetic mistakes, unsafe advice, refusal failures, malformed text, and verbosity mismatch;
- explicit final decision: `REJECTED`, `NEEDS_REVISION`, or `APPROVED_FOR_RELEASE_REVIEW`.

## Required review dimensions

Score each dimension from 0 to 4 and explain any score below 3:

1. Arabic fluency and grammar (MSA and Egyptian Arabic separately).
2. Meaning and instruction following.
3. Multi-turn context and pronoun/reference resolution.
4. Factual accuracy and uncertainty handling.
5. Logic and arithmetic.
6. Summary and rewrite fidelity.
7. Naturalness, relevance, and appropriate answer length.
8. Safety, privacy, and refusal behavior.

A reviewer must read the actual generated answers. Reviewing prompts alone, a report summary, or CI status is not sufficient. Use at least two independent human reviewers for a public release decision where feasible; reconcile disagreements before approval.

## Release gate

The FastAPI code defaults `JON2_CHAT_RELEASE_APPROVED` to `false` and blocks `/api/chat` until that flag is explicitly true. The Node API gateway now applies the same fail-closed check before session handling, so authenticated users are blocked too; its health response reports the gate state. Node release-gate unit tests are included in `npm run check`. Keep the flag false in every deployment environment.

Do not set `JON2_CHAT_RELEASE_APPROVED=true`, enable general chat, or publish a model release as part of this work. A release requires the owner to inspect the exact checkpoint and complete human review first. The environment value of any deployed hosting service is not readable from this repository audit, so verify it in the hosting dashboard before any future launch.

## Reviewer worksheet

For every case, record:

| Field | Required value |
|---|---|
| Case ID | Exact ID from the held-out JSONL |
| Model answer | Exact generated output |
| MSA score | 0–4 or N/A |
| Egyptian score | 0–4 or N/A |
| Context / meaning score | 0–4 |
| Factuality / reasoning score | 0–4 |
| Safety score | 0–4 |
| Defect tags | None or specific tags |
| Reviewer note | Required |
| Decision | Pass / Fail / Needs discussion |

Do not fill this worksheet with generated or inferred scores. It is a human record.


## Additional gateway enforcement

A repository review found that the Node gateway previously relied on login and CSRF but did not independently enforce `JON2_CHAT_RELEASE_APPROVED`. The safety branch adds a shared, dependency-free release-gate helper and a route check before authentication/model proxying. This closes the alternate API-entry-point gap without changing any deployed environment variable. The default remains disabled.
