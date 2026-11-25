# Jon2 private checkpoint runtime (preview preparation)

This change prepares the original Jon2 runtime to retrieve its approved checkpoint
from the project's **private** Vercel Blob store. It does not publish weights,
enable public chat, or deploy the API.

## Server environment

- `BLOB_READ_WRITE_TOKEN`: supplied by the connected private Blob store; server-side only.
- `JON2_CHECKPOINT_BLOB`: optional exact pathname, either `jon2-last.pt` (default)
  or `jon2-small.pt`.
- `JON2_CHECKPOINT_CACHE`: optional writable cache directory; defaults to
  `/tmp/jon2-checkpoints`.

The downloader accepts only the two reviewed checkpoint names and their
pre-recorded SHA-256 digests. It downloads to a temporary file, enforces a
20 MiB maximum, atomically renames the completed file, and verifies the digest
before the model loader can read it. The Blob token is never returned by an API.

## Safety gates

- Model retrieval is lazy; health-only requests do not download weights.
- The existing inference, human-review, and release-approval gates remain closed.
- A configured Blob source is not reported as a loaded or quality-approved model.
- This branch is preparation only. No Production deployment or main-branch change
  is part of this work.

## Deployment constraint to resolve before preview

The current project uses a static-only `vercel.json` build allowlist and does not
yet expose the FastAPI application as a Vercel Python entrypoint. The repository's
root `requirements.txt` also includes PyTorch and image-generation packages.
Vercel documents a 500 MB uncompressed Python Function bundle limit, so the
dependency set and routing must be measured and separated before enabling a
Python deployment. Do not enable chat or merge this branch until a Preview build,
private Blob integrity check, and human quality evaluation pass.
