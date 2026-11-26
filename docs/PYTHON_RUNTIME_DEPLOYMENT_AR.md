# Jon2 AI Python runtime deployment

This Blueprint defines a **health-only, opt-in Render service** for the original
Jon2 FastAPI application. It does not create a service merely by being merged.
The owner must review and apply the Blueprint in Render.

## Current safety state

- `JON2_CHAT_RELEASE_APPROVED=false` is explicit and must remain false.
- No Kaggle credential is configured by this Blueprint. The entrypoint therefore
  starts in health-only mode and does not fetch private weights.
- No checkpoint, dataset, approval manifest, or runtime token is stored in Git.
- `JON2_RUNTIME_TOKEN` is a required secret to be entered in the Render
  dashboard when the Blueprint is applied. Use a unique random value of at
  least 32 characters and configure the same value as a Cloudflare secret only
  after the Python service is actually deployed and verified.
- `/api/health/live` verifies process liveness only. It does not mean the
  model is loaded, usable, or approved.

## Apply only after owner review

1. Open the Render Blueprint flow for this GitHub repository.
2. Review the proposed `jon2-ai-python-runtime` service and its Free plan.
3. Keep `JON2_CHAT_RELEASE_APPROVED=false`.
4. Supply `JON2_RUNTIME_TOKEN` through Render's secret prompt. Never put it in
   GitHub, source files, frontend JavaScript, or chat messages.
5. Apply only if you accept the service creation and its platform terms.
6. Verify `/api/health/live` and then `/api/health`. The latter must clearly
   show the model is not ready while no reviewed checkpoint is installed.

## Important compute limitation

Render Free web services have very limited CPU and memory and are not an
approved inference target for Jon2. This Blueprint is only a low-cost process
and API integration probe. A successful build or health check is **not**
evidence that PyTorch can load the checkpoint or that inference is viable.
Do not install the Kaggle token or enable chat on this service until a separate
host-capacity test and exact-checkpoint quality review have passed.

Before production routing, the Python runtime must expose the versioned
`/v1/health` and authenticated `/v1/chat` contract. Then configure the
Cloudflare gateway's `JON2_RUNTIME_URL` and `JON2_RUNTIME_TOKEN` as secrets
in the intended Worker environment. The existing TypeScript bridge is a
preview implementation; do not switch production traffic to it without a
separate review and explicit approval.

## Current checkpoint status

The previously audited original checkpoint produced unintelligible Arabic
responses in practical testing. It is not approved for public chat. The release
flag must remain false regardless of whether the API process starts.
