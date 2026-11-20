# Jon2 AI API deployment — Hostless free runtime

The repository already contains the root `Dockerfile` and `hostless.yaml`.
Hostless is the selected first cloud host because it can run the project's
Dockerized Python/FastAPI service from GitHub and advertises an always-on free
allowance. This is a **constrained integration/runtime trial**, not a promise
that the current model will generate useful Arabic.

## What the existing configuration requests

The root `hostless.yaml` configures:
- Docker build from the repository-root `Dockerfile`.
- One web replica.
- Runtime scaling between 0.1 and 0.5 vCPU and 256 MiB to 1 GiB RAM.
- HTTP health checks at `/api/health/live`.

Hostless currently documents one shared free account allowance of 0.5 vCPU,
1 GiB RAM, and 512 MiB database storage across all the account's apps,
workers, cron jobs, and databases. Builds are not charged. The allowance is
shared, not a dedicated allocation for Jon2. Do not create extra resources or
enable paid capacity. If the account already uses some of the allowance, less
may remain for Jon2. Above-allowance usage can be billed after adding a payment
method or qualifying credit. Keep the account without a payment method if the
hard requirement is zero spend.

Hostless advertises apps as always-on without cold starts. This differs from
Render's free service, which sleeps after 15 idle minutes. Hostless does not
provide a free GPU in this allowance: Jon2 will run on CPU, capped at 0.5 vCPU
and 1 GiB RAM. That is suitable for an initial API and checkpoint-load test,
but it may be too constrained or slow for PyTorch inference. The actual host
must pass the model-load and inference tests before any readiness claim.

## Deploy from iPhone Safari

1. Open the [Hostless dashboard](https://web.hostless.cloud/) and create/sign
   in to the owner's account.
2. Connect GitHub and authorize access to `jonkabeel-star/jon2-ai`.
3. Create an app from that repository, selecting the `main` branch and the
   repository root. Hostless reads the existing `hostless.yaml` and
   `Dockerfile`; do not create a second service or database for this first
   trial.
4. Review the requested runtime cap. Keep it within the existing free
   allowance: at most 0.5 vCPU and 1 GiB RAM, one replica. Do not add a card,
   paid capacity, workers, databases, or storage add-ons.
5. Add the environment variables below in the Hostless app's Secrets/Variables
   settings. Never place secret values in GitHub files or in the public
   website.
6. Deploy and inspect the build/runtime logs. A successful deployment only
   proves that the container started; it does not prove that the model loaded
   or that its Arabic output is good.

## Runtime environment

Set these variables in the Hostless dashboard:

| Name | Value / handling |
|---|---|
| `JON2_CHECKPOINT` | `/app/model-weights/jon2-last.pt` |
| `JON2_PRELOAD_MODEL` | `true` (attempt to load the original checkpoint on startup) |
| `KAGGLE_API_TOKEN` | Secret: a Kaggle API token that can read the private Jon2 checkpoint dataset |
| `JON2_RUNTIME_TOKEN` | Secret: a newly generated random value of at least 32 characters |
| `JON2_CHAT_RELEASE_APPROVED` | `false` |
| `JON2_INFERENCE_TESTED` | `false` |
| `JON2_QUALITY_REVIEW_PASSED` | `false` |
| `JON2_EXPERIMENTAL_CHAT` | `false` |

The Docker entrypoint downloads only the configured checkpoint file from the
private Kaggle dataset. It does not make the dataset public. If Kaggle returns
401/403, stop and fix the private token/permission; do not change dataset
visibility. The checkpoint file is not committed to this repository.

`JON2_PRELOAD_MODEL=true` only asks the API to load the checkpoint. It does
not set inference approval or open chat. The three release flags above must
remain false. The runtime's `/api/health` endpoint should report process,
checkpoint, and model-load states separately. `/api/health/ready` and chat
must remain unavailable until the exact checkpoint passes evaluation and
human review.

## Verification sequence

After deployment, use the app's HTTPS URL:

1. `/api/health/live` — process liveness only.
2. `/api/health` — inspect `checkpoint_configured`, `model_loaded`,
   `inference_tested`, `quality_review_passed`, and `chat_ready`.
3. `/api/health/ready` — expected to return HTTP 503 while release gates are
   false.
4. Do not connect the public GitHub Pages frontend yet. Keep
   `jon2-config.js` empty until the API, authentication boundary, CORS, and
   end-to-end request path have been verified.

The Python API's `/v1/chat` requires the private `JON2_RUNTIME_TOKEN`.
The browser must never receive that token. The public website must not call
this private route directly. A secure gateway is required before public chat.

## Data, storage, and security limits

- The free runtime is CPU-only; no free GPU is included in this Hostless
  allowance.
- The free CPU/RAM allowance is shared across the account and may be reduced
  by other projects.
- Do not assume local SQLite files or downloaded checkpoint files are durable
  across container replacement. The checkpoint is re-downloaded from the
  private dataset at startup; persistent conversation storage is not part of
  this first deployment.
- Do not put Kaggle tokens, runtime tokens, model weights, training corpora,
  or approval manifests in the repository.
- Do not enable public chat, experimental chat, or any fallback model.
- If the container is killed for memory or inference is unusably slow, keep
  chat closed. Do not add paid resources without the owner's explicit consent.

## Current model limitation

The currently documented Jon2 checkpoint previously produced incoherent
Arabic and failed the practical conversation-quality gate. A healthy API,
successful Docker build, readable checkpoint, or `model_loaded=true` is not
a quality pass. The public release flags remain false until a fresh held-out
Arabic evaluation and human semantic review both pass.

## Official Hostless references

- [Free allowance](https://docs.hostless.cloud/plans/free-tier)
- [Free resource limits](https://docs.hostless.cloud/plans/limits)
- [Hostless deployment configuration](https://docs.hostless.cloud/app/hostlessfile)
