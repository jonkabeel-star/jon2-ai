# Jon2 AI API deployment notes

This directory contains the original Jon2 FastAPI service. The repository root
contains a CPU-only Dockerfile and a Render Blueprint (render.yaml) for a
locked, health-checkable API deployment.

## Safe first deployment

The Render Blueprint targets the Frankfurt region on the Free plan and deploys the API with
JON2_CHAT_RELEASE_APPROVED=false. Its platform health check uses `/api/health/live`, which only verifies that the API process responds; `/api/health` reports model status separately. The chat endpoint must
remain unavailable until a real checkpoint passes held-out evaluation and
human review.

The runtime now imports the PyTorch model code lazily. A service without a
checkpoint can start and report API health without importing the heavy model
runtime. This is a startup optimization only; it does not make inference
available or reduce the memory needed to load a model.

## Deploy the locked API from an iPhone

The repository includes a Render Blueprint at `render.yaml`. This is a deployment recipe, not a deployed service. The project owner must sign in to the hosting provider and authorize access to this GitHub repository; repository automation cannot create that account authorization on the owner's behalf.

For an initial health-only deployment:

1. Open the hosting provider's dashboard in Safari and choose its Blueprint/new-from-repository flow.
2. Connect `jonkabeel-star/jon2-ai` and select the `main` branch.
3. Let the provider read the root `render.yaml` and review the proposed service named `jon2-ai-api`.
4. Keep `JON2_CHAT_RELEASE_APPROVED=false`. Do not add a checkpoint, training corpus, approval manifest, or secret to the repository.
5. After the provider finishes deploying, open the service's HTTPS `/api/health/live` address to confirm process liveness, then `/api/health` to inspect model status. `/api/health/ready` should return HTTP 503 until a reviewed checkpoint is actually ready.
6. Do not set `window.JON2_API_BASE_URL` in the public website until the HTTPS health endpoint and CORS behavior have been checked.

The host's dashboard, account, repository authorization, and deployment URL are owner-controlled. No deployment has been performed merely by committing this Blueprint. A free health-only deployment also does not prove that the host can load or serve the PyTorch model; the free Render resource limits documented below are not suitable evidence of inference capacity.

## Container configuration

The image installs FastAPI, Uvicorn, and the CPU-only PyTorch wheel. It does not
bundle model checkpoints or training data. Container platforms should provide:
- PORT (the Dockerfile defaults to 8000);
- JON2_CHECKPOINT pointing to a privately mounted checkpoint, once one has
  passed evaluation and human review;
- JON2_CHAT_RELEASE_APPROVED=true only after the exact deployed checkpoint
  has passed the full held-out evaluation and human approval.

Never put a checkpoint, approval manifest, API token, or training corpus in the
public Git repository or Docker image.

## Health and release behavior

- GET / confirms that the API process responds.
- GET /api/health/live checks only that the API process responds.
- GET /api/health reports checkpoint presence, model loading, release approval, and the combined `chat_ready` state.
- GET /api/health/ready returns HTTP 503 until a real checkpoint is loaded and its release is approved.
- POST /api/chat remains HTTP 503 unless explicit release approval is set and a usable checkpoint is available.

A successful container build or health check does not mean the model is useful.

## Hosting limitations

Render's Free web services currently have 512 MB RAM, 0.1 CPU, spin down after
15 minutes without traffic, and have ephemeral local filesystems. They are
suitable only for an initial API/health integration test here, not a promise
that PyTorch inference will fit or run acceptably. Model inference must be
measured on the actual host before release. See
https://render.com/docs/free and https://render.com/docs/compute-plans.

Hugging Face Docker Spaces support FastAPI containers, but current account
requirements mean free CPU Basic Docker Spaces require a PRO subscription;
they are not a no-subscription free deployment path. See
https://huggingface.co/docs/hub/spaces-overview and
https://huggingface.co/docs/hub/spaces-sdks-docker.

The model API and the static GitHub Pages frontend are separate services. Set
window.JON2_API_BASE_URL in the frontend only after a real HTTPS backend has
been deployed and its health endpoint has been checked.
