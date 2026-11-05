# Jon2 Arabic — Compute and hosting decision

**Decision: no permanent free notebook-hosted API. Use notebook GPUs only for permitted, interactive, temporary experiments.**

Last reviewed: 2026-11-05

## Why the iPhone is not the inference host

The iPhone 12 Pro Max is the control device for editing the repository, reviewing results, and using the eventual web interface. It is not a viable host for the current 8B BF16 candidate. The device has 6 GB RAM, while 8B BF16 weights alone are roughly 16 GB before runtime memory, context/KV cache, and the operating system.

## Free notebook services: permitted use

### Google Colab free

Google's official FAQ says free resources are dynamic and not guaranteed; free sessions may run for at most 12 hours depending on availability and usage. The FAQ also explicitly prohibits file hosting, media serving, web-service offerings unrelated to interactive compute, remote proxies, and distributed workers on free managed runtimes.

Official source: https://research.google.com/colaboratory/faq.html

**Jon2 decision:** use Colab only for allowed interactive notebook work and short experiments. Do not expose Jon2's API through a tunnel, keep a server running, or use it as permanent hosting.

### Kaggle Notebooks

Kaggle's official notebook documentation describes free GPU access subject to availability and queues. The published environment specifications describe temporary sessions (up to 12 hours) and finite notebook storage. Kaggle's GPU usage guide describes a weekly GPU quota that can vary with resource availability.

Official sources:
- https://www.kaggle.com/docs/notebooks
- https://www.kaggle.com/docs/efficient-gpu-usage

**Jon2 decision:** Kaggle may be evaluated for an interactive, temporary model-load and quality test after rights approval. It is not a permanent public API host, and we must not promise continuous uptime.


### Hugging Face Spaces ZeroGPU (newly evaluated)

Hugging Face's current official documentation describes a free ZeroGPU option for eligible personal accounts: up to two hosted ZeroGPU Spaces, Gradio SDK only, with dynamic NVIDIA RTX Pro 6000 Blackwell allocation. The documented free-account GPU quota is 5 minutes per day, with queueing and availability constraints. This is a shared, quota-limited demo environment, not a guaranteed always-on production service.

Official sources:
- https://huggingface.co/docs/hub/spaces-zerogpu
- https://huggingface.co/docs/hub/spaces-overview

**Jon2 decision:** keep this as a possible *temporary interactive inference proof-of-concept* after the rights and HF access gates are cleared. It may be enough to test a short real conversation on a GPU, but the daily quota, Gradio-only integration, queue, and lack of guaranteed uptime make it unsuitable as the permanent Jon2 API. Do not publish model weights, access tokens, or private prompts in the Space repository or client code. Any gated model token must be stored only as a Space secret, and the Space visibility/access implications must be reviewed before deployment.

## What a real inference host must provide

Before selecting or paying for any host, verify all of the following against the exact model format and runtime:

- enough system RAM or GPU VRAM for model weights plus runtime overhead and context/KV cache;
- persistent private storage for model weights and the SHA-256 manifest;
- a supported Python/runtime and model architecture;
- HTTPS ingress, authentication, rate limits, and secret management if an API is exposed;
- a clear cost ceiling and a shutdown plan;
- no requirement to send user prompts to an unrelated hosted inference provider.

A quantized checkpoint can reduce memory needs, but a smaller file size alone does not prove that the model will load or run. Validate the exact quantization, runtime compatibility, and license/provenance before adoption.

## Current execution gates

1. **Rights gate:** remain blocked until the model publisher supplies adequate written clarification about training-data sources, licenses, and permissions. A model-card license alone does not settle every upstream training-data question.
2. **Access gate:** the owner must personally review and accept any model-host access conditions.
3. **Compute gate:** select a compatible host only after the exact checkpoint format and memory requirements are known.
4. **Download gate:** use the guarded downloader with an immutable revision and private target path.
5. **Inference gate:** load locally with network access disabled for inference; record real memory use and latency.
6. **Release gate:** pass the Arabic evaluation suite and human review before enabling public chat.

## Honest current status

- The iPhone is the control device, not the model host.
- The original Jon2 engine remains separate and is not approved for public chat.
- Jais 2 adapter and API routes are code only; no checkpoint has been downloaded and no Jais 2 inference has run.
- No permanent free compute host has been verified.
- No tunnel or notebook runtime is being treated as production hosting.
