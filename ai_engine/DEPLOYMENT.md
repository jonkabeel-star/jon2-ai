# Jon2 AI API deployment notes

This directory contains the original Jon2 FastAPI service. The repository root
contains a CPU-only Dockerfile and a Render Blueprint (render.yaml) for a
locked, health-checkable API deployment.

## Safe first deployment

The Render Blueprint deploys the API with
JON2_CHAT_RELEASE_APPROVED=false. This allows the service health endpoint
to be checked without exposing unreviewed model output. The chat endpoint must
remain unavailable until a real checkpoint passes held-out evaluation and
human review.

The runtime now imports the PyTorch model code lazily. A service without a
checkpoint can start and report API health without importing the heavy model
runtime. This is a startup optimization only; it does not make inference
available or reduce the memory needed to load a model.

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
- GET /api/health reports checkpoint presence, model loading, release
  approval, and the combined chat_ready state.
- POST /api/chat remains HTTP 503 unless explicit release approval is set
  and a usable checkpoint is available.

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
