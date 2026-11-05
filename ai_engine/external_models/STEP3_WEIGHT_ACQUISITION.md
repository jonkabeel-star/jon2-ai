# Jon2 AI — Step 3: Real checkpoint acquisition

**Current state: PREPARED, NOT DOWNLOADED.**

This step is for acquiring the real Jais 2 8B Chat checkpoint into private runtime storage. It is not complete until the approved immutable revision is downloaded, every file is hashed, and the checkpoint is loaded successfully in a compatible host.

## Why the download is still blocked

The candidate is `inception42/Jais-2-8B-Chat`. Its public model card declares Apache-2.0 for the model release, but the source-level training-data inventory and permissions needed by Jon2's policy have not been supplied in the reviewed public materials. The owner also requires explicit acceptance of the Hugging Face access conditions.

Do not bypass either gate. Do not download, fine-tune, or deploy the checkpoint until both are resolved.

## What is now implemented

`download_approved_checkpoint.py` is a fail-closed downloader. It:

- accepts only the exact selected repository ID;
- requires an immutable 40-character commit SHA, not a moving `main` branch;
- requires explicit owner-set approval flags for data rights and Hub access terms;
- writes weights only to a private path outside this Git repository;
- never prints or commits the Hub token;
- computes SHA-256 and byte size for every downloaded file;
- writes a private `jon2_checkpoint_manifest.json` alongside the files.

The downloader does not send prompts or conversation data to any inference provider. Its only network activity is fetching the checkpoint files from the model host after approval.

## Required private environment settings

Set these only after personally completing the two approvals:

- `JON2_MODEL_RIGHTS_APPROVED=YES`
- `JON2_HF_ACCESS_ACCEPTED=YES`
- `JON2_MODEL_REVISION=<reviewed 40-character commit SHA>`
- `JON2_MODEL_TARGET=<private directory outside the Git repository>`
- `HF_TOKEN=<your private Hugging Face token>` (only if the repository requires it)

Then run:

```bash
python ai_engine/external_models/download_approved_checkpoint.py
```

Never put these values in GitHub source files, GitHub Pages, notebook output, screenshots, or a public issue. Do not store model files in the repository.

## Device and storage reality

The iPhone 12 Pro Max has 6 GB RAM, not 16 GB. The published Jais 2 GGUF variants range from about 4.8 GiB for Q4_K_M to 16.2 GiB for BF16. Even a quantized file is not the same as total runtime memory: the operating system, model runtime, context/KV cache, and other apps need memory too. The iPhone remains the control/interface device; inference needs a separate compatible host.

## Completion checklist

- [ ] Publisher provides adequate written source-level training-data rights clarification.
- [ ] Owner reviews and accepts the official model access conditions.
- [ ] Owner selects and records an immutable model revision.
- [ ] Download runs on a compatible private host with adequate RAM/VRAM and storage.
- [ ] Private SHA-256 manifest is generated and checked.
- [ ] Model loads locally with network access disabled for inference.
- [ ] First real Egyptian Arabic prompt returns generated text.
- [ ] Evaluation suite and human review pass before any public chat activation.

Until those checks are complete, do not describe Jon2 Arabic as downloaded, running, or ready.
