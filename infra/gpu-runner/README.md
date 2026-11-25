# Jon2 private GPU runner (manual provisioning)

This folder describes the private training host. It does not create a cloud instance or spend money.

## Recommended first host

For the current `arabic_30m` research profile, start with **one NVIDIA A40 48 GB** or L40S 48 GB GPU, 16+ vCPU, 64+ GB system RAM, and a **persistent 100–200 GB volume**. The 48 GB GPU is a capacity starting point, not proof the training workload fits; the smoke test and CUDA memory check decide.

RunPod's published pricing page currently lists A40 48 GB at about **$0.59/GPU-hour** and L40S 48 GB at about **$1.09/GPU-hour**; rates, availability, region, secure/community tier, storage and taxes can change. A40 compute examples: 4 hours ≈ $2.36; 10 hours ≈ $5.90; 20 hours ≈ $11.80, excluding storage and tax. Verify the final price in the provider checkout before creating a Pod. Prefer an isolated Secure Cloud offering for private corpora; do not use a public/community host for confidential data unless you have assessed its isolation and terms.

- Provider pricing: https://www.runpod.io/pricing
- GitHub runner docs: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners
- PyTorch CUDA installation selector: https://pytorch.org/get-started/locally/

## Required host layout

Attach a persistent volume mounted at `/workspace` before running the bootstrap script. The script creates:

- `/workspace/jon2/data` — private raw/normalized corpus and private `source_approvals.json`
- `/workspace/jon2/checkpoints` — split files, reports, and checkpoints
- `/workspace/jon2/checkpoints/candidates` — candidate-only weights

Keep the Git checkout and Actions runner work directory outside the data/checkpoint folders. Set repository **Variables** (not Git files) to these exact paths:

- `JON2_PRIVATE_DATA_DIR=/workspace/jon2/data`
- `JON2_PRIVATE_CHECKPOINT_DIR=/workspace/jon2/checkpoints`

No Hugging Face token, GitHub runner token, or private dataset file belongs in Git or workflow logs.

## GitHub registration (one-time)

1. In the private repository open **Settings → Actions → Runners → New self-hosted runner**.
2. Select **Linux → x64**. GitHub shows a short-lived registration token and commands. The token is valid only briefly; do not paste it into chat, a Git file, or a screenshot.
3. On the GPU host, use a dedicated non-root runner account. Install/configure the Actions runner with the repository URL and the short-lived token. Set custom label exactly `jon2-gpu`; default labels `self-hosted`, `linux`, and `x64` are added by GitHub.
4. Install it as a service and start it. Confirm GitHub shows **Idle/Online** and all four labels: `self-hosted`, `linux`, `x64`, `jon2-gpu`.
5. Never run untrusted fork pull-request code on this machine. The training workflow is manual-dispatch only; keep the runner scoped to this private repository and stop the Pod when not training.

GitHub routes jobs only when every `runs-on` label matches. The host must remain running and connected to GitHub over outbound HTTPS/443.

## Host bootstrap

Run `bootstrap.sh` as the dedicated runner account after mounting the persistent volume. It checks Linux x64, NVIDIA driver visibility, CUDA-enabled PyTorch, volume capacity and creates private directories. It does not install GPU drivers, register the runner, download datasets, or start training.

## GPU environment

Use a provider image with NVIDIA drivers and CUDA already installed. Install a CUDA-enabled PyTorch wheel that matches the host driver and chosen CUDA platform using the official PyTorch selector. Do not install `ai_engine/requirements.txt` on this host: that file deliberately pins the CPU-only wheel for the web API. Do not overwrite the GPU PyTorch install with a CPU wheel.

The runner must pass:

- `nvidia-smi` lists the GPU and driver.
- `python -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"`
- At least 80 GiB free on the persistent volume before corpus intake; 100–200 GB volume is recommended.

## Data rights and staging

The updated registry contains 10 candidates. None is auto-approved. Initial candidates to review:

- ShawarmaChats: 28,500 train / 1,512 test conversations across MSA, Egyptian and Maghrebi; generated from Wikipedia, AI-generated then rated/repaired, with CC BY-SA 4.0. Strong structure, but ShareAlike and Wikipedia derivative obligations need written legal review before training.
- Alexandria: human-translated, multi-turn, Egyptian subset ~1.7K rows; CC BY-NC 4.0. Keep its official split metadata. Small and domain-limited.
- 4FACTORS Egyptian sample: 50 native-written Q&A pairs, CC BY-NC 4.0. Useful as a tiny human-written smoke/evaluation set, not a training corpus.
- NileChat FineWeb-Edu Egypt: 5.52M rows / 11.2 GB, machine-translated text, CC BY-NC 4.0 and gated access requiring account-information agreement. Do not accept the gate automatically; text-only pretraining adapter is needed.
- TheArabicPile Conversational: preview shows Reddit-derived posts/comments and multiple Arabic dialects; it is not necessarily dialogue. Text-only candidate with upstream-rights and privacy review, not dialogue training.
- ArSyra: current card says the public repository contains a 50-record preview; full 34,880 dataset is paid. Gated contact-information agreement and CC BY-NC-SA terms need separate consent and legal review.
- User-generated YouTube comments and TV-subtitle sources stay quarantined until underlying rights/privacy are proven.

The current trainer's dialogue path requires JSONL conversations with alternating user/assistant turns. Text-only corpora require a separately reviewed text-pretraining pipeline; do not manufacture assistant turns from articles or comments. Do not start training with only the tiny dialogue samples.

## Workflow gates

The GitHub workflow is manual and requires the exact confirmation string. It checks the runner, CUDA, private paths, exact-file approval manifest, 3-way split, capacity preflight, and candidate-only checkpoint output. The held-out test partition is not loaded by the trainer. A candidate still needs separate semantic evaluation and human review; no automatic release approval is granted.

## Shutdown and cost control

Stop the Pod/instance when the runner is not being used. Persistent volume storage may continue to bill while the GPU is stopped. Confirm storage and compute billing separately in the provider dashboard. Never leave an idle GPU running just to keep the runner online.
