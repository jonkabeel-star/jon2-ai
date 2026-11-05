# Jon2 AI API deployment notes

This directory contains the original Jon2 FastAPI service. The repository root
also contains a CPU-only `Dockerfile` suitable for container platforms.

## Container start

The image installs FastAPI, Uvicorn, and the CPU-only PyTorch wheel. It does not
bundle model checkpoints or training data. The service starts with chat release
approval disabled. This is intentional.

Container platforms should provide:
- a writable temporary directory only if runtime cache files are needed;
- `PORT` (the Dockerfile defaults to 8000);
- `JON2_CHECKPOINT` pointing to a privately mounted checkpoint, once one has
  passed evaluation and human review;
- `JON2_CHAT_RELEASE_APPROVED=true` only after the exact deployed checkpoint
  has passed the full held-out evaluation and human approval.

Never put a checkpoint, approval manifest, API token, or training corpus in the
public Git repository or Docker image.

## Health and release behavior

- `GET /` confirms that the API process responds.
- `GET /api/health` reports checkpoint presence, model loading, release
  approval, and the combined `chat_ready` state.
- `POST /api/chat` remains HTTP 503 unless explicit release approval is set
  and a usable checkpoint is available.

A successful container build or health check does not mean the model is useful.

## Free-hosting limitations

A free container host can be useful for API integration tests, but it is not
automatically suitable for model inference. For example, Render's free web
services have 512 MB RAM, spin down after 15 minutes without traffic, and have
ephemeral local storage. The Jon2 runtime imports PyTorch and needs a checkpoint;
measure actual peak memory before selecting a host. Do not assume a free service
can run inference reliably or keep private weights on its local filesystem.

The model API and the static GitHub Pages frontend are separate services. Set
`window.JON2_API_BASE_URL` in the frontend only after a real HTTPS backend has
been deployed and its health endpoint has been checked.
